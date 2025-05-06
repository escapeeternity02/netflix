import os
import json
import asyncio
import time
import random
import re
from telethon import TelegramClient, events, errors
from aiohttp import web
from colorama import Fore, init
from collections import deque

init(autoreset=True)

CREDENTIALS_FOLDER = "sessions"
LOG_RECEIVER = "EscapeEternity"
MAX_DMS_PER_HOUR = 4

# Expanded keyword detection
KEYWORDS = [
    "need", "want", "buy", "get", "have", "month", "screen", "account",
    "plan", "premium", "login", "cheap", "seller", "netflix"
]
KEYWORD_PATTERN = re.compile(r"|".join(rf"\b{k}\b" for k in KEYWORDS), re.IGNORECASE)

REPLY_MSG = "DM! I have in cheap."
DM_MSG = """NETFLIX FULLY PRIVATE SCREEN ACCOUNT!!
Price - 79rs/1$
4K PREMIUM PLAN
1 MONTH FULL WARRANTY 
SEPARATE PROFILE + PIN 
FULLY PRIVATE & SECURED

ALWAYS ESCROW 
DM ~ @EscapeEternity"""
FOLLOWUP_MSG = "This is BotAccount so DM @EscapeEternity for Anything!"

messaged_users = {}
dm_queue = deque()
last_hour_timestamp = 0
dm_sent_this_hour = 0

def normalize_text(text):
    return re.sub(r'[^\w\s]', '', text.lower())

async def start_web_server():
    async def handle(request):
        return web.Response(text="Service is running!")

    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000)))
    await site.start()
    print(Fore.YELLOW + "Web server started.")

async def dm_worker(client):
    global last_hour_timestamp, dm_sent_this_hour
    while True:
        now = time.time()
        if now - last_hour_timestamp >= 3600:
            dm_sent_this_hour = 0
            last_hour_timestamp = now

        if dm_queue and dm_sent_this_hour < MAX_DMS_PER_HOUR:
            user, msg = dm_queue.popleft()
            try:
                await client.send_message(user, msg)
                print(Fore.GREEN + f"[DM SENT] -> {user.id}")
                dm_sent_this_hour += 1
            except Exception as e:
                print(Fore.RED + f"[DM ERROR] {e}")
        await asyncio.sleep(15)

async def handle_session(session_path):
    with open(session_path, "r") as f:
        credentials = json.load(f)

    session_name = os.path.splitext(os.path.basename(session_path))[0]
    proxy = tuple(credentials.get("proxy", [])) or None

    client = TelegramClient(
        os.path.join(CREDENTIALS_FOLDER, session_name),
        credentials["api_id"],
        credentials["api_hash"],
        proxy=proxy
    )

    await client.connect()
    if not await client.is_user_authorized():
        print(Fore.RED + f"[{session_name}] Session unauthorized.")
        return

    print(Fore.GREEN + f"[{session_name}] Running...")

    asyncio.create_task(dm_worker(client))

    @client.on(events.NewMessage(incoming=True))
    async def keyword_handler(event):
        try:
            if event.is_private or event.out or event.fwd_from:
                return  # Skip private, outgoing or forwarded messages

            message_text = normalize_text(event.raw_text)
            if not KEYWORD_PATTERN.search(message_text) or "netflix" not in message_text:
                return

            group = await event.get_chat()
            user = await event.get_sender()
            user_id = user.id
            username = user.username or "no username"
            key = f"{user_id}"

            now = time.time()
            if key in messaged_users and now - messaged_users[key] < 3600:
                print(Fore.MAGENTA + f"[{session_name}] Skipping repeat user: {username}")
                return

            await event.reply(REPLY_MSG)
            print(Fore.CYAN + f"[{session_name}] Replied in group: {group.title} -> {username}")

            messaged_users[key] = now
            dm_queue.append((user, DM_MSG))

            # Logging to console
            print(Fore.YELLOW + f"[{session_name}] Queued DM to {username} ({user_id})")

            # Logging to main account
            log_msg = f"""
📣 Netflix Triggered

👤 [{username}](tg://user?id={user_id})
🆔 {user_id}
💬 {event.raw_text}
👥 Group: {group.title}
"""
            await client.send_message(LOG_RECEIVER, log_msg)

        except Exception as e:
            print(Fore.RED + f"[{session_name}] Handler error: {e}")

    await client.run_until_disconnected()

async def main():
    os.makedirs(CREDENTIALS_FOLDER, exist_ok=True)
    json_files = [os.path.join(CREDENTIALS_FOLDER, f) for f in os.listdir(CREDENTIALS_FOLDER) if f.endswith(".json")]

    if not json_files:
        print(Fore.RED + "No session .json files found.")
        return

    print(Fore.GREEN + f"Loading {len(json_files)} session(s)...")

    tasks = [handle_session(f) for f in json_files]
    tasks.append(start_web_server())

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())

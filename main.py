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

# Keyword triggers
KEYWORDS = [
    "need", "want", "buy", "get", "have", "month", "screen", "account",
    "plan", "premium", "login", "cheap", "seller", "selling", "netflix"
]

REPLY_MSG = "DM! I have in cheap."
DM_MSG = """NETFLIX FULLY PRIVATE SCREEN ACCOUNT!!
Price - 79rs/1$
4K PREMIUM PLAN
1 MONTH FULL WARRANTY 
SEPARATE PROFILE + PIN 
FULLY PRIVATE & SECURED

ALWAYS ESCROW 
DM ~ @EscapeEternity"""

PRIVATE_DM_RESPONSE = (
    "This is a Bot Selling Account! To Buy DM @EscapeEternity Only. "
    "If Limited Then DM @EscapeEternityBot"
)

dm_queue = deque()
dm_timestamps = []
messaged_users = set()  # Tracks who already got a DM


def normalize_text(text):
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
    return text.lower()


def contains_keywords(text):
    return "netflix" in text and any(k in text for k in KEYWORDS if k != "netflix")


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
    while True:
        now = time.time()
        # Remove old timestamps outside 1 hour
        while dm_timestamps and now - dm_timestamps[0] > 3600:
            dm_timestamps.pop(0)

        if dm_queue and len(dm_timestamps) < MAX_DMS_PER_HOUR:
            user, msg = dm_queue.popleft()
            try:
                await client.send_message(user, msg)
                dm_timestamps.append(time.time())
                print(Fore.GREEN + f"[DM SENT] -> {user.id}")
            except Exception as e:
                print(Fore.RED + f"[DM ERROR] {e}")

        await asyncio.sleep(10)


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
    async def group_keyword_handler(event):
        try:
            if event.is_private or event.out or event.fwd_from:
                return

            message_text = normalize_text(event.raw_text)
            if not contains_keywords(message_text):
                return

            group = await event.get_chat()
            user = await event.get_sender()
            user_id = user.id
            username = user.username or "no username"

            print(Fore.CYAN + f"[{session_name}] Trigger -> {user_id} in {group.title}: {event.raw_text}")

            # Always reply in group
            try:
                await event.reply(REPLY_MSG)
                print(Fore.YELLOW + f"[{session_name}] Replied in group {group.title}")
            except Exception as e:
                print(Fore.RED + f"[{session_name}] Group reply failed: {e}")

            # DM only if not already messaged this session
            if user_id not in messaged_users and len(dm_timestamps) < MAX_DMS_PER_HOUR:
                dm_queue.append((user, DM_MSG))
                messaged_users.add(user_id)
                print(Fore.MAGENTA + f"[{session_name}] Queued DM to {username}")

            # Log to admin
            try:
                log_msg = f"""
📣 Netflix Triggered

👤 [{username}](tg://user?id={user_id})
🆔 {user_id}
💬 {event.raw_text}
👥 Group: {group.title}
"""
                await client.send_message(LOG_RECEIVER, log_msg)
                print(Fore.LIGHTBLUE_EX + f"[{session_name}] Logged to {LOG_RECEIVER}")
            except Exception as e:
                print(Fore.RED + f"[{session_name}] Log failed: {e}")

        except Exception as e:
            print(Fore.RED + f"[{session_name}] Handler error: {e}")

    @client.on(events.NewMessage(incoming=True, chats=None))
    async def handle_private_message(event):
        if event.is_private:
            try:
                await event.respond(PRIVATE_DM_RESPONSE)
                print(Fore.LIGHTGREEN_EX + f"[{session_name}] Auto-replied to DM from {event.sender_id}")
            except Exception as e:
                print(Fore.RED + f"[{session_name}] DM auto-reply error: {e}")

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

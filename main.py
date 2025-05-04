import os
import json
import asyncio
import time
import random
import re
from telethon import TelegramClient, events, errors
from aiohttp import web
from colorama import Fore, init

init(autoreset=True)

CREDENTIALS_FOLDER = "sessions"
LOG_RECEIVER = "EscapeEternity"

# Regular expression for detecting Netflix-related keywords
KEYWORD_PATTERN = re.compile(r"(need|want|buy|get|have|month|screen|account|plan|premium|login|cheap).*?netflix", re.IGNORECASE)

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

# Track messaged users to avoid re-spamming
messaged_users = {}

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

    @client.on(events.NewMessage(incoming=True))
    async def keyword_handler(event):
        try:
            if event.is_private:
                return  # We only care about group messages for this bot

            message_text = event.raw_text.lower()

            # Check if the message matches Netflix-related keywords using regex
            if KEYWORD_PATTERN.search(message_text):
                group = await event.get_chat()
                user = await event.get_sender()
                user_id = user.id
                username = user.username or "no username"
                key = f"{user_id}"

                # Avoid double messages per user (1 message per hour max)
                now = time.time()
                if key in messaged_users and now - messaged_users[key] < 3600:
                    return

                # Reply in group
                try:
                    await event.reply(REPLY_MSG)
                except errors.ChatWriteForbiddenError:
                    print(Fore.RED + f"[{session_name}] Banned from group: {group.title}")
                    return
                except errors.FloodWaitError as e:
                    print(Fore.YELLOW + f"[{session_name}] Flood wait: {e.seconds}s")
                    await asyncio.sleep(e.seconds + 2)
                    return

                # Delay before DM (human-like)
                await asyncio.sleep(random.randint(3, 7))

                # DM user
                try:
                    await client.send_message(user, DM_MSG)
                    messaged_users[key] = now
                except Exception as e:
                    print(Fore.RED + f"[{session_name}] DM failed: {e}")
                    return

                # Log to main account
                try:
                    log_msg = f"""
📣 Netflix Triggered

👤 [{username}](tg://user?id={user_id})
🆔 {user_id}
💬 {event.raw_text}
👥 Group: {group.title}
"""
                    await client.send_message(LOG_RECEIVER, log_msg)
                except Exception as e:
                    print(Fore.RED + f"[{session_name}] Log DM failed: {e}")

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

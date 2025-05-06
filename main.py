import os
import json
import asyncio
import time
import random
import re
from telethon import TelegramClient, events, errors
from collections import deque
from colorama import Fore, init
from aiohttp import web

init(autoreset=True)

LOG_RECEIVER = "EscapeEternity"
MAX_DMS_PER_HOUR = 4

# Admin list (replace with your actual user ID)
admin_ids = [123456789]  # Replace with your admin user ID here

# Keywords for Netflix-related messages
KEYWORDS = [
    "need", "want", "buy", "get", "have", "month", "screen", "account",
    "plan", "premium", "login", "cheap", "seller", "selling", "netflix"
]

# Default messages
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

# Track sent messages and DM queue
dm_queue = deque()
dm_timestamps = []
messaged_users = set()  # To avoid sending multiple DMs to the same user

def normalize_text(text):
    return re.sub(r'[^\w\s]', '', text).lower()

def contains_keywords(text):
    return "netflix" in text and any(k in text for k in KEYWORDS if k != "netflix")

# Web server to keep the app alive (useful for cloud hosting platforms)
async def start_web_server():
    async def handle(request):
        return web.Response(text="Service is running!")  # A simple endpoint to keep the service alive

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

async def handle_session():
    # Set up the credentials directly or use environment variables for API ID and Hash
    api_id = os.getenv("API_ID")  # Set this environment variable in Render
    api_hash = os.getenv("API_HASH")  # Set this environment variable in Render
    session_name = "bot_session"  # Use a default session name (no need for files)
    client = TelegramClient(session_name, api_id, api_hash)

    await client.connect()
    if not await client.is_user_authorized():
        print(Fore.RED + f"Session unauthorized.")
        return

    print(Fore.GREEN + f"Running...")

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

            print(Fore.CYAN + f"Trigger -> {user_id} in {group.title}: {event.raw_text}")

            try:
                await event.reply(REPLY_MSG)
                print(Fore.YELLOW + f"Replied in group {group.title}")
            except Exception as e:
                print(Fore.RED + f"Group reply failed: {e}")

            if user_id not in messaged_users and len(dm_timestamps) < MAX_DMS_PER_HOUR:
                dm_queue.append((user, DM_MSG))
                messaged_users.add(user_id)
                print(Fore.MAGENTA + f"Queued DM to {username}")

            try:
                log_msg = f"""
📣 Netflix Triggered

👤 [{username}](tg://user?id={user_id})
🆔 {user_id}
💬 {event.raw_text}
👥 Group: {group.title}
"""
                await client.send_message(LOG_RECEIVER, log_msg)
                print(Fore.LIGHTBLUE_EX + f"Logged to {LOG_RECEIVER}")
            except Exception as e:
                print(Fore.RED + f"Log failed: {e}")

        except Exception as e:
            print(Fore.RED + f"Handler error: {e}")

    @client.on(events.NewMessage(incoming=True, chats=None))
    async def handle_private_message(event):
        if event.is_private:
            try:
                await event.respond(PRIVATE_DM_RESPONSE)
                print(Fore.LIGHTGREEN_EX + f"Auto-replied to DM from {event.sender_id}")
            except Exception as e:
                print(Fore.RED + f"DM auto-reply error: {e}")

    await client.run_until_disconnected()

async def main():
    # Directly run the session handling without using file-based credentials
    await handle_session()
    await start_web_server()

if __name__ == "__main__":
    asyncio.run(main())

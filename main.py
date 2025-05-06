import os
import json
import asyncio
import random
import re
from telethon import TelegramClient, events, errors
from colorama import Fore, init
from aiohttp import web
from collections import deque

# Initialize colorama for console output
init(autoreset=True)

# Constants
LOG_RECEIVER = "EscapeEternity"  # Replace with your log receiver username or ID
MAX_DMS_PER_HOUR = 4  # Max DMs allowed per hour

# Keywords for Netflix-related messages (case-insensitive)
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

# Function to normalize text (case-insensitive)
def normalize_text(text):
    return re.sub(r'[^\w\s]', '', text).lower()

# Function to check if a message contains Netflix-related keywords
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

# Function to send DMs in a controlled manner (with hourly limits)
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

# Function to handle login and sessions
async def handle_login():
    session_name = "bot_session"
    path = os.path.join("sessions", f"{session_name}.json")

    if not os.path.exists(path):
        print(Fore.RED + f"Credentials file {path} not found.")
        return

    with open(path, "r") as f:
        credentials = json.load(f)

    proxy = credentials.get("proxy")
    proxy_args = tuple(proxy) if proxy else None

    client = TelegramClient(
        os.path.join("sessions", session_name),
        credentials["api_id"],
        credentials["api_hash"],
        proxy=proxy_args
    )

    await client.connect()
    if not await client.is_user_authorized():
        print(Fore.RED + "Session not authorized.")
        return client

    print(Fore.GREEN + f"Logged in as {client.get_me().username}")
    return client

# Function to handle keyword-triggered actions
async def handle_keyword_trigger(client, event):
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

# Function to handle direct messages to the bot
async def handle_private_message(event):
    if event.is_private:
        try:
            await event.respond(PRIVATE_DM_RESPONSE)
            print(Fore.LIGHTGREEN_EX + f"Auto-replied to DM from {event.sender_id}")
        except Exception as e:
            print(Fore.RED + f"DM auto-reply error: {e}")

# Main function
async def main():
    client = await handle_login()

    if not client:
        return

    await client.start()

    # Handling incoming group messages
    @client.on(events.NewMessage(incoming=True))
    async def keyword_handler(event):
        await handle_keyword_trigger(client, event)

    # Handling incoming DMs
    @client.on(events.NewMessage(incoming=True, chats=None))
    async def dm_handler(event):
        await handle_private_message(event)

    await asyncio.gather(
        start_web_server(),
        dm_worker(client)  # Start the DM worker to process queued DMs
    )

if __name__ == "__main__":
    asyncio.run(main())

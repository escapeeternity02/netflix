import os
import json
import asyncio
from telethon import TelegramClient, events, errors
from telethon.tl.functions.messages import SendMessageRequest
from telethon.tl.types import PeerUser
from aiohttp import web
from colorama import Fore, init

init(autoreset=True)

CREDENTIALS_FOLDER = "sessions"
LOG_RECEIVER = "EscapeEternity"

KEYWORDS = [
    "need netflix", "netflix", "need", "need nf", "nf need", "netflix screen need",
    "need netflix screen", "netflix chaiye", "i need netflix", "netflix monthly need",
    "need month netflix", "1 month netflix", "netflix account", "want netflix",
    "netflix login", "buy netflix", "netflix required", "monthly netflix", "cheap netflix"
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
FOLLOWUP_MSG = "This is BotAccount so DM @EscapeEternity for Anything!"

async def start_web_server():
    async def handle(request):
        return web.Response(text="Service is running!")

    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 10000)))
    await site.start()
    print(Fore.YELLOW + "Web server started to keep service alive.")

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
        print(Fore.RED + f"[{session_name}] Not authorized!")
        return

    print(Fore.GREEN + f"[{session_name}] Connected.")

    @client.on(events.NewMessage(incoming=True))
    async def keyword_handler(event):
        try:
            if event.is_group and any(k in event.raw_text.lower() for k in KEYWORDS):
                await event.reply(REPLY_MSG)

                user = await event.get_sender()
                user_id = user.id
                username = user.username or "No username"
                msg_text = event.raw_text
                group = await event.get_chat()
                group_name = group.title if hasattr(group, "title") else str(group.id)

                # Send DM
                await client.send_message(PeerUser(user_id), DM_MSG)

                @client.on(events.NewMessage(from_users=user_id))
                async def followup(ev):
                    await client.send_message(PeerUser(user_id), FOLLOWUP_MSG)

                log_msg = f"""
🚨 Netflix Keyword Triggered!

👤 User: [{username}](tg://user?id={user_id})
🆔 User ID: {user_id}
💬 Message: {msg_text}
👥 Group: {group_name}
"""
                await client.send_message(LOG_RECEIVER, log_msg)
        except Exception as e:
            print(Fore.RED + f"[{session_name}] Error: {e}")

    await client.run_until_disconnected()

async def main():
    os.makedirs(CREDENTIALS_FOLDER, exist_ok=True)
    json_files = [os.path.join(CREDENTIALS_FOLDER, f) for f in os.listdir(CREDENTIALS_FOLDER) if f.endswith(".json")]

    if not json_files:
        print(Fore.RED + "No session .json files found.")
        return

    print(Fore.GREEN + f"Starting {len(json_files)} session(s)...")

    tasks = [handle_session(f) for f in json_files]
    tasks.append(start_web_server())

    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())

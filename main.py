import os
import asyncio
from telethon import TelegramClient, events
from telethon.tl.functions.messages import SendMessageRequest
from telethon.tl.types import PeerUser

API_ID = int(os.getenv("TG_API_ID"))
API_HASH = os.getenv("TG_API_HASH")
LOG_RECEIVER = "EscapeEternity"  # No @ needed

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

async def start_clients():
    tasks = []
    for session_file in os.listdir("sessions"):
        if session_file.endswith(".session"):
            session_name = session_file.replace(".session", "")
            client = TelegramClient(f"sessions/{session_name}", API_ID, API_HASH)

            @client.on(events.NewMessage(chats=None))
            async def handler(event):
                if event.is_group and any(k in event.raw_text.lower() for k in KEYWORDS):
                    try:
                        await event.reply(REPLY_MSG)

                        user = await event.get_sender()
                        user_id = user.id
                        username = user.username or "No username"
                        msg_text = event.raw_text

                        # Send DM
                        await client(SendMessageRequest(PeerUser(user_id), DM_MSG))

                        # Wait for any reply to send follow-up
                        @client.on(events.NewMessage(from_users=user_id))
                        async def reply_back(ev):
                            await client(SendMessageRequest(PeerUser(user_id), FOLLOWUP_MSG))

                        # Log to owner
                        log_msg = f"""
🚨 Keyword Triggered!

👤 User: [{username}](tg://user?id={user_id})
🆔 User ID: {user_id}
💬 Message: {msg_text}
👥 Group: {event.chat.title}
"""
                        await client.send_message(LOG_RECEIVER, log_msg)

                    except Exception as e:
                        print(f"Error handling message: {e}")

            tasks.append(client.start())
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(start_clients())

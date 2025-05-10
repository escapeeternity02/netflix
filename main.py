import os
import json
import asyncio
import re
from telethon import TelegramClient, events
from aiohttp import web
from colorama import Fore, init

init(autoreset=True)

CREDENTIALS_FOLDER = "sessions"
LOG_RECEIVER = "EscapeEternity"

admin_ids = [6249999953]
blacklisted_users = set()

KEYWORDS = [
    "need", "want", "buy", "get", "have", "month", "screen", "account",
    "plan", "premium", "login", "cheap", "seller", "selling", "netflix"
]

REPLY_MSG = "DM karo! Sasta milega."
DM_MSG = """NETFLIX FULLY PRIVATE SCREEN ACCOUNT!!
Price - ₹79 / $1
4K PREMIUM PLAN
1 MONTH FULL WARRANTY 
SEPARATE PROFILE + PIN 
FULLY PRIVATE & SECURED

ALWAYS ESCROW 
DM ~ @EscapeEternity"""

PRIVATE_DM_RESPONSE = (
    "Yeh bot hai jo accounts bechta hai! Kharidne ke liye sirf @EscapeEternity ko DM karo. "
    "Agar limited ho toh @EscapeEternityBot ko DM karo."
)

current_dm_msg = DM_MSG
current_group_msg = REPLY_MSG

dm_sent_users = set()

def normalize_text(text):
    text = re.sub(r'[^\w\s]', '', text)
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
    async def group_keyword_handler(event):
        try:
            if event.is_private or event.out or event.fwd_from:
                return

            user = await event.get_sender()
            user_id = user.id
            if user_id in blacklisted_users:
                return

            message_text = normalize_text(event.raw_text)
            if not contains_keywords(message_text):
                return

            group = await event.get_chat()
            username = user.username or "no username"

            print(Fore.CYAN + f"[{session_name}] Trigger -> {user_id} in {group.title}: {event.raw_text}")

            try:
                await event.reply(current_group_msg)
                print(Fore.YELLOW + f"[{session_name}] Replied in group {group.title}")
            except Exception as e:
                print(Fore.RED + f"[{session_name}] Group reply failed: {e}")

            if user_id not in dm_sent_users:
                try:
                    await client.send_message(user, current_dm_msg)
                    dm_sent_users.add(user_id)
                    print(Fore.MAGENTA + f"[{session_name}] Sent DM to {username}")
                except Exception as e:
                    print(Fore.RED + f"[{session_name}] DM failed: {e}")

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

    @client.on(events.NewMessage(incoming=True))
    async def handle_private_message(event):
        if event.is_private:
            try:
                await event.respond(PRIVATE_DM_RESPONSE)
                print(Fore.LIGHTGREEN_EX + f"[{session_name}] Auto-replied to DM from {event.sender_id}")
            except Exception as e:
                print(Fore.RED + f"[{session_name}] DM auto-reply error: {e}")

    @client.on(events.NewMessage(incoming=True))
    async def admin_commands(event):
        if event.is_private and event.sender_id in admin_ids:
            msg = event.raw_text.strip()
            command = msg.lower()

            if command == "/pause":
                print(Fore.GREEN + f"[{session_name}] DM sending paused by admin")
                await event.respond("✅ DM sending paused.")
                global dm_sent_users
                dm_sent_users = set()
            elif command == "/resume":
                print(Fore.GREEN + f"[{session_name}] DM sending resumed by admin")
                await event.respond("✅ DM sending resumed.")
            elif command == "/status":
                await event.respond(f"Users who received DM: {len(dm_sent_users)}")
            elif command == "/clearqueue":
                dm_sent_users.clear()
                await event.respond("✅ DM user list cleared.")
            elif command.startswith("/addadmin"):
                parts = msg.split()
                if len(parts) > 1:
                    new_admin_id = int(parts[1])
                    if new_admin_id not in admin_ids:
                        admin_ids.append(new_admin_id)
                        await event.respond(f"✅ Added new admin: {new_admin_id}")
                    else:
                        await event.respond("❌ This user is already an admin.")
                else:
                    await event.respond("❌ Please provide a valid user ID.")
            elif command.startswith("/removeadmin"):
                parts = msg.split()
                if len(parts) > 1:
                    remove_admin_id = int(parts[1])
                    if remove_admin_id in admin_ids:
                        admin_ids.remove(remove_admin_id)
                        await event.respond(f"✅ Removed admin: {remove_admin_id}")
                    else:
                        await event.respond("❌ This user is not an admin.")
                else:
                    await event.respond("❌ Please provide a valid user ID.")
            elif command == "/shutdown":
                await event.respond("🔴 Shutting down bot...")
                await client.disconnect()
            elif command.startswith("/send"):
                parts = msg.split(maxsplit=2)
                if len(parts) == 3:
                    user_id = int(parts[1])
                    message = parts[2]
                    try:
                        user = await client.get_entity(user_id)
                        await client.send_message(user, message)
                        await event.respond(f"✅ Message sent to {user_id}")
                    except Exception as e:
                        await event.respond(f"❌ Error sending message: {e}")
            elif command.startswith("/changedmmsg"):
                new_msg = msg[13:].strip()
                if new_msg:
                    global current_dm_msg
                    current_dm_msg = new_msg
                    await event.respond(f"✅ DM message updated.")
                else:
                    await event.respond("❌ Please provide a valid message.")
            elif command.startswith("/changegroupmsg"):
                new_msg = msg[16:].strip()
                if new_msg:
                    global current_group_msg
                    current_group_msg = new_msg
                    await event.respond(f"✅ Group reply message updated.")
                else:
                    await event.respond("❌ Please provide a valid message.")
            elif command.startswith("/blacklist"):
                parts = msg.split()
                if len(parts) > 1:
                    username = parts[1].lstrip("@")
                    try:
                        user = await client.get_entity(username)
                        blacklisted_users.add(user.id)
                        await event.respond(f"✅ User @{username} has been blacklisted.")
                    except Exception as e:
                        await event.respond(f"❌ Error blacklisting user: {e}")
                else:
                    await event.respond("❌ Please provide a username to blacklist.")
            elif command == "/help":
                help_text = (
                    "Available admin commands:\n\n"
                    "/pause - Pauses DM sending\n"
                    "/resume - Resumes DM sending\n"
                    "/status - Shows current DM queue size\n"
                    "/clearqueue - Clears the DM queue\n"
                    "/addadmin <user_id> - Adds a new admin\n"
                    "/removeadmin <user_id> - Removes an admin\n"
                    "/shutdown - Shuts down the bot\n"
                    "/send <user_id> <message> - Sends a message manually\n"
                    "/changedmmsg <message> - Changes DM message\n"
                    "/changegroupmsg <message> - Changes group reply message\n"
                    "/blacklist <username> - Blacklists a user\n"
                )
                await event.respond(help_text)

    await client.run_until_disconnected()

async def main():
    os.makedirs(CREDENTIALS_FOLDER, exist_ok=True)
    json_files = [os.path.join(CREDENTIALS_FOLDER, f) for f in os.listdir(CREDENTIALS_FOLDER) if f.endswith(".json")]

    if not json_files:
        print(Fore.RED + "No session .json files found.")
        return

    print(Fore.GREEN + f"Loading {len(json_files
::contentReference[oaicite:21]{index=21}
 

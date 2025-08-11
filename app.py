import asyncio
import os
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import (
    RPCError,
    ChannelPrivateError,
    ChannelInvalidError,
    MessageIdInvalidError,
    UserNotParticipantError
)
from flask import Flask
from threading import Thread
import re

# === KONFIGURASI ===
API_ID = 24139581
API_HASH = '3615dbe983baa65ef705df6ec858b486'
SESSION = "1BVtsOKEBuz5Dg2-z8QQs3AVVkAKjT9VjaUOkRAy3LvlMev00p2exXbjhrCYZNO3s0cKNZzQKeia5LW5g2OrydeGE9P5wPuS3ZFcRxDb_PhsrCZJ5M2pXWrTRClFeMQdBoAhOymGLto1aFAOdXxIdRQjUoknyg37J8kgyJPYEyReJp5YJ7Ww93COayf_uFSlIqJmAPWz1p6Zuoi9JwO-aVH2NAA4MbJuvczYZ75ye0Hs2xTY0iYOMMaPXrbWH3NXGKeC10l2Dtu1rNwsr1EH04HbjfInnhG0ZHbP6DLLbWsya36lulcqJx_gCoXjbiSfynHcEZLBFqewWq9oDEBJyRFyBKGB5uPI="

client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)

toxic_words = {
    # Kata kasar lengkap
    "kontol", "anjing", "bangsat", "tai", "brengsek", "goblok",
    "bajingan", "asu", "kampret", "memek", "jancok", "babi",
    "gila", "setan", "tolol", "bangke", "bacot", "goblog",
    "tai kontol", "bajingan", "bajing", "bajingaan", "pantek",
    "monyet", "monyet", "bajingan", "goblok", "brengsek",
    
    # Singkatan/slang
    "kontl", "anjg", "bgst", "bjn", "gblk", "jancuk", "jancok",
    "tolol", "bacot", "babi", "asu", "memek", "kampret",
    "babi", "anjg", "bgst", "bjn", "gblk", "jancuk",

    # Variasi dan slang lain
    "pantek", "panteq", "pantekk", "pantekkk", "pantekq",
    "bgsd", "bgsd", "bgsd", "bgsd",  # variasi kasar
    "anjeng", "anjengk", "anjengkk", "anjengq",
    
    # Variasi campuran
    "tai anjg", "tai anjeng", "tai anjing", "tai bgsd"
}

@client.on(events.NewMessage(incoming=True))
async def auto_reply(event):
    if event.is_private and not event.out:
        text = event.raw_text.lower().strip()

        if text in toxic_words:
            for _ in range(10):
                await event.reply("Eh, santuy bro! 😅")
            return

        replies_text = {
            "al": "Yo, ini Al nih 😎, ada apa bro?",
            "al azet": "Al Azet siap sedia 💪, ngomong aja santai.",
            "azet": "Azet di sini 😁, santuy aja, ga usah serius-serius.",
            "fandi": "Fandi hadir 👋, santai aja bro, gue di sini.",
            "zufda": "Zufda on 🤙, jangan sungkan, langsung aja ngomong."
        }

        if text in replies_text:
            await event.reply(replies_text[text])

# === Regex untuk menangkap link t.me dengan query opsional (misal ?single) ===
link_regex = re.compile(r'(?:https?://)?t\.me/(c/\d+|[a-zA-Z0-9_]+)/(\d+)(?:\?.*?)?', re.IGNORECASE)

@client.on(events.NewMessage(pattern=r'^/(save|s)(?:\s+|$)(.*)'))
async def save_handler(event):
    input_text = event.pattern_match.group(2).strip()

    # Jika tidak ada input, coba ambil dari reply pesan
    if not input_text:
        if event.is_reply:
            reply = await event.get_reply_message()
            if reply and reply.message:
                input_text = reply.message.strip()
            else:
                await event.reply("❌ Pesan balasan tidak berisi teks.")
                return
        else:
            await event.reply("❌ Kirim atau reply link seperti `https://t.me/c/123456789/123`.")
            return

    parts = input_text.split(maxsplit=1)
    target_chat_raw = None
    links_part = input_text

    if len(parts) == 2:
        possible_target = parts[0]
        if re.match(r'^@?[a-zA-Z0-9_]+$', possible_target) or re.match(r'^-?\d+$', possible_target):
            target_chat_raw = possible_target
            links_part = parts[1]

    if target_chat_raw:
        if re.match(r'^-?\d+$', target_chat_raw):
            target_chat = int(target_chat_raw)
        else:
            target_chat = target_chat_raw
    else:
        target_chat = None

    matches = link_regex.findall(links_part)

    if not matches:
        await event.reply("❌ Tidak ada link yang valid ditemukan.")
        return

    loading = await event.reply(f"⏳ Memproses {len(matches)} link...")

    for chat_part, msg_id in matches:
        await process_link(event, chat_part, int(msg_id), target_chat=target_chat)

    try:
        await loading.delete()
    except:
        pass


async def process_link(event, chat_part, msg_id, target_chat=None):
    try:
        if chat_part.startswith("c/"):
            internal_id = chat_part[2:]
            chat_id = int(f"-100{internal_id}")
            try:
                await client.get_permissions(chat_id, 'me')
            except (UserNotParticipantError, ChannelInvalidError, ChannelPrivateError):
                await event.reply(f"🚫 Ubot belum join channel tersebut.\n`{chat_part}`")
                return
        else:
            try:
                entity = await client.get_entity(chat_part)
                if getattr(entity, "username", None):
                    chat_id = chat_part
                else:
                    chat_id = entity.id
                    try:
                        await client.get_permissions(chat_id, 'me')
                    except (UserNotParticipantError, ChannelInvalidError, ChannelPrivateError):
                        await event.reply(f"🚫 Ubot belum join channel `{chat_part}`.")
                        return
            except (ChannelInvalidError, ValueError):
                await event.reply(f"❌ Channel/grup `{chat_part}` tidak ditemukan.")
                return

        message = await client.get_messages(chat_id, ids=msg_id)
        if not message:
            await event.reply(f"❌ Pesan {msg_id} di `{chat_part}` tidak ditemukan.")
            return

        send_to = target_chat or event.chat_id

        grouped_id = message.grouped_id
        if grouped_id:
            all_msgs = await client.get_messages(chat_id, limit=200)
            same_group = [m for m in all_msgs if m.grouped_id == grouped_id]
            same_group.sort(key=lambda m: m.id)

            files = []
            first_buttons = None
            first_caption = None

            for m in same_group:
                if first_buttons is None:
                    btns = getattr(m, 'buttons', None)
                    if btns:
                        first_buttons = btns

                if first_caption is None and (m.message or m.raw_text):
                    first_caption = m.message or m.raw_text

                if m.media:
                    fpath = await client.download_media(m.media)
                    files.append(fpath)
                else:
                    if m.message or m.raw_text:
                        await client.send_message(send_to, m.message or m.raw_text,
                                                  buttons=first_buttons if first_buttons else None,
                                                  link_preview=False)

            if files:
                caption = first_caption or f"✅ Media group dari [pesan ini](https://t.me/{chat_part}/{msg_id})"
                await client.send_file(send_to,
                                       file=files,
                                       caption=caption,
                                       link_preview=False,
                                       buttons=first_buttons if first_buttons else None)
                for p in files:
                    try:
                        os.remove(p)
                    except:
                        pass

        else:
            buttons = getattr(message, 'buttons', None)
            text_content = message.message or message.raw_text or ""
            if message.media:
                fpath = await client.download_media(message.media)
                caption = message.text or text_content or f"✅ Media dari [pesan ini](https://t.me/{chat_part}/{msg_id})"
                await client.send_file(send_to,
                                       file=fpath,
                                       caption=caption,
                                       link_preview=False,
                                       buttons=buttons if buttons else None)
                try:
                    os.remove(fpath)
                except:
                    pass
            elif text_content:
                await client.send_message(send_to,
                                          f"{text_content}",
                                          buttons=buttons if buttons else None,
                                          link_preview=False)
            else:
                await client.send_message(send_to,
                                          f"⚠️ Pesan tidak berisi teks maupun media.\n[Klik di sini](https://t.me/{chat_part}/{msg_id}) untuk melihat.",
                                          buttons=buttons if buttons else None,
                                          link_preview=False)

    except MessageIdInvalidError:
        await event.reply(f"❌ ID pesan `{msg_id}` tidak valid.")
    except RPCError as e:
        await event.reply(f"🚨 Kesalahan RPC: `{str(e)}`")
    except Exception as e:
        await event.reply(f"🚨 Terjadi kesalahan: `{str(e)}`")


# === REPLIT UPTIME ===
app = Flask(__name__)

@app.route('/')
def home():
    return "Ubot aktif!", 200

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()

# === JALANKAN ===
keep_alive()
client.start()
print("Ubot aktif.")
client.run_until_disconnected()

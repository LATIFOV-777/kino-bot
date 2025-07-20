import json
import os
import sqlite3
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from telegram.error import BadRequest

from dotenv import load_dotenv

load_dotenv()

#Sozlamalar
TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 6515136056))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@kino_premyera2")
KANAL = os.getenv("KANAL", "@latifov_7777")
# === SQLITE DB ===
DB_PATH = "data/users.db"
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (chat_id INTEGER PRIMARY KEY)")
conn.commit()

# Foydalanuvchini saqlash
def save_user(chat_id):
    try:
        cursor.execute("INSERT OR IGNORE INTO users (chat_id) VALUES (?)", (chat_id,))
        conn.commit()
    except Exception as e:
        print(f"[XATOLIK] Foydalanuvchini saqlashda: {e}")

# Kodlar fayli
DATA_FILE = "data/kodlar.json"
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        f.write("{}")

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

kodlar = load_data()

# Broadcast yuborish funksiyasi
async def send_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Sizda ruxsat yo'q.")
        return

    text = ' '.join(context.args)
    if not text:
        await update.message.reply_text("❗ Xabar matnini kiriting: /sendall <matn>")
        return

    cursor.execute("SELECT chat_id FROM users")
    users = cursor.fetchall()
    count = 0
    for (chat_id,) in users:
        try:
            await context.bot.send_message(chat_id=chat_id, text=text)
            count += 1
        except Exception as e:
            print(f"⚠️ Yuborilmadi {chat_id}: {e}")

    await update.message.reply_text(f"✅ {count} ta foydalanuvchiga yuborildi.")

# Obuna tekshirish
async def is_subscribed(user_id, context):
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except BadRequest as e:
        print(f"❌ Xatolik: {e}")
        return False



# /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    save_user(user_id)

    if user_id == ADMIN_ID:
        await update.message.reply_text("👑 Siz adminsiz. /admin menyudan foydalaning.")
        return

    if await is_subscribed(user_id, context):
        await update.message.reply_text("🎥 Salom! Kino olish uchun kod yuboring.")
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Kanalga obuna bo‘lish", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")],
            [InlineKeyboardButton("📢 Kanalga obuna bo‘lish", url=f"https://t.me/{KANAL.strip('@')}")],
            [InlineKeyboardButton("✅ Tekshirish", callback_data="check_subscription")]
        ])
        await update.message.reply_text("📢 Botdan foydalanish uchun avval kanalga obuna bo‘ling:", reply_markup=keyboard)

# Tekshir tugmasi
async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if await is_subscribed(user_id, context):
        await query.edit_message_text("✅ Obuna tasdiqlandi! Endi kod yuboring.")
    else:
        await query.edit_message_text("🚫 Hali ham kanalga obuna bo‘lmagansiz.")

# /admin menyusi
async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Siz admin emassiz.")
        return
    await update.message.reply_text(
        "👑 Admin menyusi:\n"
        "/add - kod qo‘shish\n"
        "/del - kod o‘chirish\n"
        "/list - kodlar ro‘yxati\n"
        "/sendall - xabar yuborish barchaga\n"
        "/info - bot haqida ma'lumot"
    )

# /info komandasi
async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    info_text = (
        "ℹ️ <b>Bot haqida:</b>\n"
        "📌 Bu bot orqali siz maxfiy kodlar orqali kinolarni olishingiz mumkin.\n"
        "📢 Botdan foydalanish uchun <a href='https://t.me/{0}'>kanalga obuna</a> bo'lishingiz shart.\n"
        "💬 Savollar va reklamar uchun: @Pro_admin7"
    ).format(CHANNEL_USERNAME.strip("@"))
    await update.message.reply_text(info_text, parse_mode="HTML")

# Kod qo‘shish
async def add_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Siz admin emassiz.")
        return

    args = context.args
    if len(args) < 1:
        await update.message.reply_text("❗ Foydalanish:\n/add <kod> <link> yoki reply qilib /add <kod>")
        return

    kod = args[0]

    if update.message.reply_to_message:
        msg = update.message.reply_to_message
        kodlar[kod] = [msg.chat.id, msg.message_id]  # FIXED: chat_id => chat.id
    elif len(args) >= 2:
        link = " ".join(args[1:])
        kodlar[kod] = link
    else:
        await update.message.reply_text("⚠️ Xatolik: reply yoki link yo‘q.")
        return

    save_data(kodlar)
    await update.message.reply_text(f"✅ Kod qo‘shildi: {kod}")

# Kod o‘chirish
async def del_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Siz admin emassiz.")
        return

    args = context.args
    if len(args) != 1:
        await update.message.reply_text("❗ Foydalanish: /del <kod>")
        return

    kod = args[0]
    if kod in kodlar:
        del kodlar[kod]
        save_data(kodlar)
        await update.message.reply_text(f"🗑️ Kod o‘chirildi: {kod}")
    else:
        await update.message.reply_text("🚫 Bunday kod yo‘q.")

# Kodlar ro‘yxati
async def list_codes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Siz admin emassiz.")
        return

    if not kodlar:
        await update.message.reply_text("📭 Hech qanday kod yo‘q.")
    else:
        text = "📄 Kodlar ro‘yxati:\n"
        for k, v in kodlar.items():
            text += f"🔑 {k} → {v}\n"
        await update.message.reply_text(text)

# Kodlarni ishlovchi handler
async def handle_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_subscribed(user_id, context) and user_id != ADMIN_ID:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Kanalga obuna bo‘lish", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")],
            [InlineKeyboardButton("📢 Kanalga obuna bo‘lish", url=f"https://t.me/{KANAL.strip('@')}")],
            [InlineKeyboardButton("✅ Tekshirish", callback_data="check_subscription")]
        ])
        await update.message.reply_text("🚫 Avval kanalga obuna bo‘ling:", reply_markup=keyboard)
        return

    code = update.message.text.strip()
    if code in kodlar:
        value = kodlar[code]
        if isinstance(value, list) and len(value) == 2:
            try:
                await context.bot.copy_message(
                    chat_id=update.effective_chat.id,
                    from_chat_id=value[0],
                    message_id=value[1]
                )
            except Exception as e:
                print(f"Xatolik kino yuborishda: {e}")
                await update.message.reply_text("⚠️ Xatolik: Kino yuborilmadi.")
        elif isinstance(value, str):
            await update.message.reply_text(f"🔗 Havola: {value}")
        else:
            await update.message.reply_text("❌ Kod topildi, lekin noto‘g‘ri formatda.")
    else:
        await update.message.reply_text("❌ Bunday kod topilmadi.")

# Fayl oxiri:
if __name__ == '__main__':
    import asyncio
    import nest_asyncio

    nest_asyncio.apply()

    async def run():
        app = ApplicationBuilder().token(TOKEN).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("admin", admin_menu))
        app.add_handler(CommandHandler("sendall", send_all))
        app.add_handler(CommandHandler("info", info_command))
        app.add_handler(CommandHandler("add", add_code))
        app.add_handler(CommandHandler("del", del_code))
        app.add_handler(CommandHandler("list", list_codes))
        app.add_handler(CallbackQueryHandler(check_subscription))
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_code))

        print("✅ Bot ishga tushdi...")
        await app.run_polling()

    asyncio.run(run())

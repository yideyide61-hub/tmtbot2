import os
import logging
import datetime
from typing import Dict, Any
from flask import Flask, request

# ======= FIX: Patch imghdr with Pillow =========
import sys, types
from PIL import Image

def what(file, h=None):
    try:
        img = Image.open(file)
        return img.format.lower()
    except Exception:
        return None

imghdr_stub = types.ModuleType("imghdr")
imghdr_stub.what = what
sys.modules["imghdr"] = imghdr_stub
# ===============================================

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
PORT = int(os.getenv("PORT", "10000"))  # Render provides PORT env
APP_URL = os.getenv("APP_URL", "https://your-app.onrender.com")  # set in Render dashboard
ADMIN_USER_IDS = {7124683213}

# Telegram Bot + Dispatcher
bot = Bot(BOT_TOKEN)
dispatcher = Dispatcher(bot, None, workers=4, use_context=True)

# Flask app
app = Flask(__name__)

# ================== STORAGE =================
group_data: Dict[int, Dict[int, Dict[str, Any]]] = {}

# ================== LOGGING =================
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================== CONSTANTS =================
ACTIVITY_LIMITS = {
    "eat": {"limit_min": 30, "fine": 10},
    "toilet": {"limit_min": 15, "fine": 10},
    "smoke": {"limit_min": 10, "fine": 10},
    "meeting": {"limit_min": 60, "fine": 0},
}
LATE_WORK_FINE = 50

NAMES = {
    "work": "上班", "off": "下班", "eat": "吃饭",
    "toilet": "上厕所", "smoke": "抽烟", "meeting": "会议", "back": "回座"
}

# ================== HELPERS (same as before) ==================
def ensure_user(chat_id: int, user_id: int, name: str):
    if chat_id not in group_data:
        group_data[chat_id] = {}
    users = group_data[chat_id]
    if user_id not in users:
        users[user_id] = {
            "name": name,
            "activities": [],
            "daily_fines": 0,
            "monthly_fines": 0,
            "work_start": None,
            "work_time": datetime.timedelta(),
            "pure_work_time": datetime.timedelta(),
            "total_activity_time": datetime.timedelta(),
        }
    return users[user_id]

def format_td(td: datetime.timedelta) -> str:
    total = int(td.total_seconds())
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    parts = []
    if h: parts.append(f"{h}小时")
    if m: parts.append(f"{m}分钟")
    if s or not parts: parts.append(f"{s}秒")
    return " ".join(parts)

def make_inline_menu() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(NAMES['work'], callback_data="work"),
         InlineKeyboardButton(NAMES['off'], callback_data="off")],
        [InlineKeyboardButton(NAMES['eat'], callback_data="eat"),
         InlineKeyboardButton(NAMES['toilet'], callback_data="toilet"),
         InlineKeyboardButton(NAMES['smoke'], callback_data="smoke")],
        [InlineKeyboardButton(NAMES['meeting'], callback_data="meeting")],
        [InlineKeyboardButton(NAMES['back'], callback_data="back")],
    ]
    return InlineKeyboardMarkup(kb)

# ================== COMMANDS ==================
def start(update: Update, context: CallbackContext):
    ensure_user(update.effective_chat.id, update.effective_user.id, update.effective_user.full_name)
    update.message.reply_text("📋 欢迎使用考勤机器人，请打卡：", reply_markup=make_inline_menu())

def report(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    if uid not in ADMIN_USER_IDS:
        update.message.reply_text("❌ 仅限管理员使用")
        return
    chat_id = update.effective_chat.id
    users = group_data.get(chat_id, {})
    lines = ["📅 每日考勤报告"]
    for u, d in users.items():
        lines.append(f"{d['name']} | 本日罚款 ${d['daily_fines']}, 本月罚款 ${d['monthly_fines']}")
    update.message.reply_text("\n".join(lines))

# ================== BUTTON HANDLER ==================
def button_handler(update: Update, context: CallbackContext):
    # (same code as your original)
    pass  # <-- keep your existing implementation here

# ================== JOBS ==================
def daily_reset(context: CallbackContext):
    # (same code as your original)
    pass

def monthly_reset(context: CallbackContext):
    # (same code as your original)
    pass

# ================== WEBHOOK HANDLER ==================
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

@app.route("/")
def home():
    return "Bot is running ✅"

def main():
    # Register handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("report", report))
    dispatcher.add_handler(CallbackQueryHandler(button_handler))

    # Setup webhook
    bot.delete_webhook()
    bot.set_webhook(url=f"{APP_URL}/{BOT_TOKEN}")

    # Start Flask app
    app.run(host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()


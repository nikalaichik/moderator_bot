from telegram import Update
from telegram.ext import ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет приветственное сообщение."""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Привет! Я бот-модератор. Я буду следить за порядком в этом чате."
    )

async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствует новых участников чата."""
    for member in update.message.new_chat_members:
        await update.message.reply_text(f"Добро пожаловать в чат, {member.full_name}!")

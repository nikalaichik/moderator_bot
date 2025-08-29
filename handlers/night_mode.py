import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus
from config import NIGHT_START_TIME, DAY_START_TIME, TIMEZONE
from telegram.constants import ChatMemberStatus
from config import NIGHT_START_TIME, DAY_START_TIME, TIMEZONE, NIGHT_MODE_CHATS
from .admin import is_admin
# Множество для хранения ID чатов, где включен ночной режим.
# ВАЖНО: При перезапуске бота это множество очистится. Для постоянного хранения
# данных потребуется использовать базу данных или файл.
NIGHT_MODE_CHATS = set()

async def enable_night_mode_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Задача, которая ВЫКЛЮЧАЕТ возможность писать сообщения для всех, кроме админов.
    """
    chat_id = context.job.chat_id
    try:
        # Устанавливаем права "только чтение" для всех участников
        await context.bot.set_chat_permissions(
            chat_id=chat_id,
            permissions=ChatPermissions(can_send_messages=False)
        )
        await context.bot.send_message(
            chat_id=chat_id,
            text="🌙 Включаю ночной режим. Чат закрыт для сообщений до 9:00."
        )
    except Exception as e:
        logging.error(f"Не удалось включить ночной режим в чате {chat_id}: {e}")

async def disable_night_mode_job(context: ContextTypes.DEFAULT_TYPE):
    """
    Задача, которая ВКЛЮЧАЕТ возможность писать сообщения для всех.
    """
    chat_id = context.job.chat_id
    try:
        # Возвращаем стандартные права
        await context.bot.set_chat_permissions(
            chat_id=chat_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
        await context.bot.send_message(
            chat_id=chat_id,
            text="☀️ Доброе утро! Чат снова открыт для общения."
        )
    except Exception as e:
        logging.error(f"Не удалось выключить ночной режим в чате {chat_id}: {e}")

async def night_mode_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда для включения ночного режима в чате.
    """
    if not await is_admin(update, context):
        await update.message.reply_text("Эта команда доступна только администраторам.")
        return

    chat_id = update.effective_chat.id
    if chat_id in NIGHT_MODE_CHATS:
        await update.message.reply_text("Ночной режим уже включен в этом чате.")
        return

    # Добавляем задачи в планировщик
    context.application.job_queue.run_daily(enable_night_mode_job, time=NIGHT_START_TIME, chat_id=chat_id, name=f"night_on_{chat_id}")
    context.application.job_queue.run_daily(disable_night_mode_job, time=DAY_START_TIME, chat_id=chat_id, name=f"night_off_{chat_id}")

    NIGHT_MODE_CHATS.add(chat_id)
    await update.message.reply_text(
        f"Ночной режим успешно включен. Чат будет закрываться с {NIGHT_START_TIME.strftime('%H:%M')} до {DAY_START_TIME.strftime('%H:%M')} "
        f"(по времени {TIMEZONE})."
    )

async def night_mode_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда для выключения ночного режима в чате.
    """
    if not await is_admin(update, context):
        await update.message.reply_text("Эта команда доступна только администраторам.")
        return

    chat_id = update.effective_chat.id
    if chat_id not in NIGHT_MODE_CHATS:
        await update.message.reply_text("Ночной режим не был включен в этом чате.")
        return

    # Находим и удаляем задачи из планировщика
    jobs_on = context.application.job_queue.get_jobs_by_name(f"night_on_{chat_id}")
    jobs_off = context.application.job_queue.get_jobs_by_name(f"night_off_{chat_id}")

    for job in jobs_on:
        job.schedule_removal()
    for job in jobs_off:
        job.schedule_removal()

    NIGHT_MODE_CHATS.remove(chat_id)

    # Принудительно возвращаем права на случай, если команду вызвали ночью
    await disable_night_mode_job(context=ContextTypes.DEFAULT_TYPE(application=context.application, chat_id=chat_id))

    await update.message.reply_text("Ночной режим отключен. Чат теперь работает 24/7.")
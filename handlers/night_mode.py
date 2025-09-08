import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes
from config import NIGHT_START_TIME, DAY_START_TIME, TIMEZONE, bot_state
from .admin import is_admin
from datetime import datetime

# Множество для хранения ID чатов, где включен ночной режим.
# ВАЖНО: При перезапуске бота это множество очистится. Для постоянного хранения
# данных потребуется использовать базу данных или файл.
#NIGHT_MODE_CHATS = set()

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
    if chat_id in bot_state.night_mode_chats:
        await update.message.reply_text("Ночной режим уже включен в этом чате.")
        return

    # Удаляем старые задачи, если они есть
    old_jobs = context.application.job_queue.get_jobs_by_name(f"night_on_{chat_id}")
    for job in old_jobs:
        job.schedule_removal()

    old_jobs = context.application.job_queue.get_jobs_by_name(f"night_off_{chat_id}")
    for job in old_jobs:
        job.schedule_removal()

    # Добавляем новые задачи
    context.application.job_queue.run_daily(
        enable_night_mode_job,
        time=NIGHT_START_TIME,
        chat_id=chat_id,
        name=f"night_on_{chat_id}"
    )
    context.application.job_queue.run_daily(
        disable_night_mode_job,
        time=DAY_START_TIME,
        chat_id=chat_id,
        name=f"night_off_{chat_id}"
    )

    bot_state.add_night_mode_chat(chat_id)

    # Проверяем, нужно ли включить ночной режим прямо сейчас
    current_time = datetime.now(TIMEZONE).time()
    if NIGHT_START_TIME <= current_time or current_time <= DAY_START_TIME:
        await enable_night_mode_job(context)
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
    if chat_id not in bot_state.night_mode_chats:
        await update.message.reply_text("Ночной режим не был включен в этом чате.")
        return

    # Удаляем задачи из планировщика
    jobs_to_remove = (
        context.application.job_queue.get_jobs_by_name(f"night_on_{chat_id}") +
        context.application.job_queue.get_jobs_by_name(f"night_off_{chat_id}")
    )

    for job in jobs_to_remove:
        job.schedule_removal()

    bot_state.remove_night_mode_chat(chat_id)

    # Принудительно возвращаем права на случай, если команду вызвали ночью
    #await disable_night_mode_job(context=ContextTypes.DEFAULT_TYPE(application=context.application, chat_id=chat_id))
    # Принудительно открываем чат
    try:
        await context.bot.set_chat_permissions(
            chat_id=chat_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
    except Exception as e:
        logging.error(f"Не удалось открыть чат при отключении ночного режима: {e}")
    await update.message.reply_text("Ночной режим отключен. Чат теперь работает 24/7.")
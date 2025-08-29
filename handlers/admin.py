import logging
from datetime import timedelta
import config
from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Проверяет, является ли пользователь, вызвавший команду, администратором чата.
    """
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    try:
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        return chat_member.status in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception as e:
        logging.error(f"Ошибка при проверке статуса администратора: {e}")
        return False

async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Исключает пользователя из чата. Команда доступна только администраторам.
    Использование: ответьте на сообщение пользователя командой /kick
    """
    if not await is_admin(update, context):
        await update.message.reply_text("Эта команда доступна только администраторам.")
        return
    # Проверяем, что команда используется в ответ на сообщение
    if not update.message.reply_to_message:
        await update.message.reply_text("Эту команду нужно использовать в ответ на сообщение пользователя.")
        return

    user_to_kick = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id

    try:
        await context.bot.unban_chat_member(chat_id=chat_id, user_id=user_to_kick.id)
        await update.message.reply_text(f"Пользователь {user_to_kick.full_name} был исключен из чата.")
    except Exception as e:
        await update.message.reply_text(f"Не удалось исключить пользователя. Ошибка: {e}")


async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Банит пользователя в чате. Команда доступна только администраторам.
    Использование: ответьте на сообщение пользователя командой /ban
    """
    if not await is_admin(update, context):
        await update.message.reply_text("Эта команда доступна только администраторам.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("Эту команду нужно использовать в ответ на сообщение пользователя.")
        return

    user_to_ban = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id

    try:
        await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_to_ban.id)
        await update.message.reply_text(f"Пользователь {user_to_ban.full_name} забанен.")
    except Exception as e:
        await update.message.reply_text(f"Не удалось забанить пользователя. Ошибка: {e}")


async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запрещает пользователю отправлять сообщения на определенное время."""
    if not await is_admin(update, context):
        await update.message.reply_text("Эта команда доступна только администраторам.")
        return

    user_to_mute = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id
    minutes = 60
    if context.args and context.args[0].isdigit():
        minutes = int(context.args[0])

    try:
        # ИСПРАВЛЕНО: Вместо вычисления даты передаем просто длительность
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_to_mute.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=timedelta(minutes=minutes)
        )
        await update.message.reply_text(f"Пользователь {user_to_mute.full_name} лишен права голоса на {minutes} минут.")
    except Exception as e:
        await update.message.reply_text(f"Не удалось ограничить пользователя. Ошибка: {e}")


async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Снимает ограничения с пользователя.
    Использование: /unmute в ответ на сообщение.
    """

    if not await is_admin(update, context):
        await update.message.reply_text("Эта команда доступна только администраторам.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Эту команду нужно использовать в ответ на сообщение пользователя.")
        return

    user_to_unmute = update.message.reply_to_message.from_user
    chat_id = update.effective_chat.id

    try:
        await context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_to_unmute.id,
            permissions={
                'can_send_messages': True,
                'can_send_media_messages': True,
                'can_send_other_messages': True,
                'can_add_web_page_previews': True
            }
        )
        await update.message.reply_text(f"С пользователя {user_to_unmute.full_name} сняты ограничения.")
    except Exception as e:
        await update.message.reply_text(f"Не удалось снять ограничения. Ошибка: {e}")

async def reload_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Перезагружает список стоп-слов из файла.
    Доступно только администраторам.
    """
# Можно добавить проверку на администратора, если нужно
    if not await is_admin(update, context):
        await update.message.reply_text("Эта команда доступна только администраторам.")
        return
    count = config.load_forbidden_words()
    await update.message.reply_text(f"✅ Список стоп-слов успешно перезагружен. Загружено слов: {count}.")
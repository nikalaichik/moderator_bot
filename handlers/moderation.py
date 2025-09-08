from datetime import datetime, timedelta, timezone
from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus
import logging
from .admin import is_admin

# Импортируем настройки из конфига
from config import (
    FORBIDDEN_WORDS,
    SPAM_MESSAGE_LIMIT,
    SPAM_TIME_WINDOW_SECONDS,
    SPAM_MUTE_DURATION_HOURS,
    bot_state
)

async def check_for_spam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Проверяет пользователя на спам. Возвращает True, если обнаружен спам."""
    user = update.effective_user
    if not user: return False

    user_id = user.id
    chat_id = update.effective_chat.id
    now = datetime.now()

    # Получаем или создаем хранилище для сообщений пользователей
    if 'user_messages' not in context.chat_data:
        context.chat_data['user_messages'] = {}

    user_messages = context.chat_data['user_messages']
    # Получаем список временных меток (timestamp) для текущего пользователя.
    # Если пользователя еще нет в словаре, для него создастся пустой список.
    timestamps = user_messages.get(user_id, [])

    # Фильтруем список: создаем новый, содержащий только "свежие" сообщения.
    recent_timestamps = [ts for ts in timestamps if (now - ts).total_seconds() < SPAM_TIME_WINDOW_SECONDS]

    # Добавляем время текущего сообщения.
    recent_timestamps.append(now)

    # Сохраняем обновленный список обратно в хранилище.
    user_messages[user_id] = recent_timestamps

    # --- Отладочная информация ---
    logging.info(
        f"[SPAM CHECK] User: {user.username} ({user_id}) | "
        f"Messages in window: {len(recent_timestamps)}/{SPAM_MESSAGE_LIMIT}"
    )

    # Проверяем, превысил ли пользователь лимит.
    if len(recent_timestamps) >= SPAM_MESSAGE_LIMIT:
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=datetime.now(timezone.utc) + timedelta(hours=SPAM_MUTE_DURATION_HOURS)
            )
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"Пользователь @{user.username} был заглушен на {SPAM_MUTE_DURATION_HOURS} часов за спам."
            )
            # Очищаем историю сообщений спамера после наказания
            user_messages[user_id] = []
            return True
        except Exception as e:
            logging.warning(f"Не удалось выдать мут за спам (возможно, это не супергруппа): {e}")

    return False

async def delete_forwarded_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаляет пересланные сообщения от обычных пользователей."""
    message = update.effective_message
    user = update.effective_user
    if not message or not user: return

    # Проверяем, является ли пользователь администратором
    if await is_admin(update, context):
        return

    try:
        await message.delete()
        username = user.username or user.first_name or "Пользователь"
        await context.bot.send_message(
        chat_id=message.chat_id,
        text=f"🚫 Сообщение от {username} удалено (пересылка запрещена).",
        disable_notification=True
    )
    except Exception as e:
        logging.error(f"Не удалось удалить пересланное сообщение: {e}")

async def filter_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Фильтрует входящие текстовые сообщения (новые и отредактированные)."""
    message = update.effective_message
    user = update.effective_user

    if not message or not user or not message.text:
        return

    # Пропускаем проверку в чатах с ночным режимом (там свои ограничения)
    if message.chat_id in bot_state.night_mode_chats:
        return

    # Пропускаем администраторов
    if await is_admin(update, context):
        return

    '''is_spam = await check_for_spam(update, context)
    if is_spam:
        return'''

    # Проверка на спам
    if await check_for_spam(update, context):
        try:
            await message.delete()
        except:
            pass  # Сообщение уже может быть удалено
        return

    # Проверка на запрещенные слова
    if any(word in message.text.lower() for word in FORBIDDEN_WORDS):
        try:
            await message.delete()
            await context.bot.send_message(
                chat_id=message.chat_id,
                text=f"🚫 Сообщение от @{user.username} удалено, т.к. содержит запрещенное слово.",
                disable_notification=True
            )
            return
        except Exception as e:
            logging.error(f"Не удалось удалить сообщение с запрещенным словом: {e}")
            return

    # Проверка только на ссылки
    if message.entities and any(e.type in ['url', 'text_link'] for e in message.entities):
        try:
            await message.delete()
            await context.bot.send_message(
                chat_id=message.chat_id,
                text=f"🚫 Сообщение от @{user.username} удалено (ссылки запрещены).",
                disable_notification=True
            )
            return
        except Exception as e:
                logging.error(f"Не удалось удалить сообщение со ссылкой: {e}")

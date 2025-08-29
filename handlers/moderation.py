from datetime import datetime, timedelta
from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes
import logging

# Импортируем настройки из конфига
from config import (
    FORBIDDEN_WORDS,
    NIGHT_MODE_CHATS,
    SPAM_MESSAGE_LIMIT,
    SPAM_TIME_WINDOW_SECONDS,
    SPAM_MUTE_DURATION_HOURS
)

async def check_for_spam(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Проверяет пользователя на спам. Возвращает True, если обнаружен спам."""
    user = update.effective_user
    if not user: return False

    user_id = user.id
    chat_id = update.effective_chat.id
    now = datetime.now()

    # Получаем словарь с сообщениями всех пользователей в этом чате.
    # setdefault гарантирует, что он будет создан, если его нет.
    user_messages = context.chat_data.setdefault('user_messages', {})

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
    print(
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
                until_date=timedelta(hours=SPAM_MUTE_DURATION_HOURS)
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

    chat_admins = await context.bot.get_chat_administrators(message.chat_id)
    admin_ids = {admin.user.id for admin in chat_admins}
    if user.id in admin_ids: return

    await message.delete()
    await context.bot.send_message(
        chat_id=message.chat_id,
        text=f"Сообщение от @{user.username} удалено (пересылка запрещена)."
    )

async def filter_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Фильтрует входящие текстовые сообщения (новые и отредактированные)."""
    message = update.effective_message
    user = update.effective_user

    if not message or not user or not message.text:
        return

    if message.chat_id in NIGHT_MODE_CHATS:
        return

    chat_admins = await context.bot.get_chat_administrators(message.chat_id)
    admin_ids = {admin.user.id for admin in chat_admins}
    if user.id in admin_ids:
        return

    is_spam = await check_for_spam(update, context)
    if is_spam:
        return

    # Проверка на запрещенные слова
    if any(word in message.text.lower() for word in FORBIDDEN_WORDS):
        await message.delete()
        await context.bot.send_message(
            chat_id=message.chat_id,
            text=f"Сообщение от @{user.username} удалено, т.к. содержит запрещенное слово."
        )
        return

    # Проверка только на ссылки
    if message.entities and any(e.type in ['url', 'text_link'] for e in message.entities):
        await message.delete()
        await context.bot.send_message(
            chat_id=message.chat_id,
            text=f"Сообщение от @{user.username} удалено (ссылки запрещены)."
        )
        return
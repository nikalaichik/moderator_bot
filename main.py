import logging
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

# Импортируем наши настройки и обработчики
import config
from handlers import common, moderation, admin, night_mode

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def main():
    # Создаем приложение
    application = ApplicationBuilder().token(config.BOT_TOKEN).build()

    # --- Регистрируем обработчики ---

    # Общие команды
    application.add_handler(CommandHandler('start', common.start))
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, common.welcome))

    # Модерация
    application.add_handler(MessageHandler(
        filters.TEXT & (~filters.COMMAND),
        moderation.filter_messages,
        block=False # block=False позволяет другим обработчикам тоже сработать, если нужно
    ))
    '''application.add_handler(MessageHandler(
        filters.TEXT & (~filters.COMMAND),
        moderation.filter_messages
    ))'''

    application.add_handler(MessageHandler(
        filters.FORWARDED,
        moderation.delete_forwarded_messages
    ))
    # Ночной режим
    application.add_handler(CommandHandler('night_mode_on', night_mode.night_mode_on))
    application.add_handler(CommandHandler('night_mode_off', night_mode.night_mode_off))

    # Команды администраторов
    application.add_handler(CommandHandler('kick', admin.kick_user, filters=filters.REPLY))
    application.add_handler(CommandHandler('ban', admin.ban_user, filters=filters.REPLY))
    application.add_handler(CommandHandler('mute', admin.mute_user, filters=filters.REPLY))
    application.add_handler(CommandHandler('unmute', admin.unmute_user, filters=filters.REPLY))
    application.add_handler(CommandHandler('reload_words', admin.reload_words))

    # Запускаем бота
    print("Бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    main()
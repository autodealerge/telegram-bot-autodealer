import logging
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from telegram.helpers import escape_markdown

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния диалога
NAME, CONTACT = range(2)

# Администраторы
ADMIN_IDS = [407994120, 6980080944]

# Кнопки меню
MENU_BUTTONS = [
    [InlineKeyboardButton("\ud83d\udce9 Оставить заявку", callback_data="request")],
    [InlineKeyboardButton("\u2753 Задать вопрос", callback_data="question")],
    [InlineKeyboardButton("\u2b50 Оставить отзыв", callback_data="feedback")],
]

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Здравствуй! Я бот AUTODEALER GE. Чем могу помочь?",
        reply_markup=InlineKeyboardMarkup(MENU_BUTTONS),
    )

# Обработка выбора кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "request":
        await query.edit_message_text("Пожалуйста, напишите Ваше имя.")
        return NAME
    elif data == "question":
        await query.edit_message_text("Напишите свой вопрос:")
        context.user_data["mode"] = "question"
        return CONTACT
    elif data == "feedback":
        await query.edit_message_text("Оставьте свой отзыв:")
        context.user_data["mode"] = "feedback"
        return CONTACT

# Получение имени
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Оставьте свой номер телефона с кодом страны и TG @username.")
    return CONTACT

# Получение контакта и отправка сообщения администраторам
async def get_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = context.user_data.get("name")
    contact = update.message.text
    username = update.effective_user.username or "без username"

    message = escape_markdown(
        f"\U0001F7E2 *Новая заявка!*\n\n"
        f"\U0001F464 Имя: {name}\n"
        f"\U0001F4DE Контакт: {contact}\n"
        f"\U0001F517 Telegram: @{username}",
        version=2,
    )

    await notify_admins(context, message)
    await update.message.reply_text("Спасибо! Мы скоро свяжемся с Вами.")
    return ConversationHandler.END

# Обработка вопросов и отзывов
async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username or "без username"
    text = escape_markdown(update.message.text, version=2)
    message = escape_markdown(
        f"❓ Вопрос от @{username}:", version=2
    ) + f"\n{text}"

    await notify_admins(context, message)
    await update.message.reply_text("Спасибо за вопрос! Мы ответим как можно скорее.")
    return ConversationHandler.END

async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username or "без username"
    text = escape_markdown(update.message.text, version=2)
    message = escape_markdown(
        f"⭐ Отзыв от @{username}:", version=2
    ) + f"\n{text}"

    await notify_admins(context, message)
    await update.message.reply_text("Спасибо за отзыв!")
    return ConversationHandler.END

# Функция рассылки администраторам
async def notify_admins(context: ContextTypes.DEFAULT_TYPE, message: str):
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        except Exception as e:
            logging.error(f"Не удалось отправить сообщение администратору {admin_id}: {e}")

# Завершение диалога
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

# Запуск бота
if __name__ == "__main__":
    application = ApplicationBuilder().token(TOKEN).build()

    conversation_request = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^request$")],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contact)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    conversation_question = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^question$")],
        states={
            CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    conversation_feedback = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^feedback$")],
        states={
            CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_feedback)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conversation_request)
    application.add_handler(conversation_question)
    application.add_handler(conversation_feedback)

    print("Бот запущен.")
    application.run_polling()

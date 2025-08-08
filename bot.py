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

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

NAME, CONTACT = range(2)
AUTO_REQUIREMENTS, AUTO_BUDGET, AUTO_CITY, AUTO_NAME, AUTO_CONTACT = range(5)

ADMIN_IDS = [407994120, 6980080944]

MENU_BUTTONS = [
    [InlineKeyboardButton("\ud83d\udce9 Оставить заявку", callback_data="request")],
    [InlineKeyboardButton("\u2753 Задать вопрос", callback_data="question")],
    [InlineKeyboardButton("\u2b50 Оставить отзыв", callback_data="feedback")],
    [InlineKeyboardButton("\ud83d\udcca Рассчитать стоимость авто", callback_data="calculate")],
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Здравствуй! Я бот AUTODEALER GE. Чем могу помочь?",
        reply_markup=InlineKeyboardMarkup(MENU_BUTTONS),
    )

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
    elif data == "calculate":
        await query.edit_message_text("Укажите ваши требования по авто (марка, модель, год выпуска, пробег...):")
        return AUTO_REQUIREMENTS

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Оставьте свой номер телефона с кодом страны и TG @username.")
    return CONTACT

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

async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username or "без username"
    text = escape_markdown(update.message.text, version=2)
    message = escape_markdown(f"❓ Вопрос от @{username}:", version=2) + f"\n{text}"

    await notify_admins(context, message)
    await update.message.reply_text("Спасибо за вопрос! Мы ответим как можно скорее.")
    return ConversationHandler.END

async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username or "без username"
    text = escape_markdown(update.message.text, version=2)
    message = escape_markdown(f"⭐ Отзыв от @{username}:", version=2) + f"\n{text}"

    await notify_admins(context, message)
    await update.message.reply_text("Спасибо за отзыв!")
    return ConversationHandler.END

# Расчет стоимости авто — шаги
async def auto_requirements(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["requirements"] = update.message.text
    await update.message.reply_text("Какую сумму (бюджет) вы готовы выделить на покупку этой машины?")
    return AUTO_BUDGET

async def auto_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["budget"] = update.message.text
    await update.message.reply_text("Из какого вы города? (чтобы мы могли посчитать доставку)")
    return AUTO_CITY

async def auto_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["city"] = update.message.text
    await update.message.reply_text("Пожалуйста напишите ваше имя")
    return AUTO_NAME

async def auto_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Пожалуйста, оставьте ваши контактные данные (номер телефона, TG @username или email)")
    return AUTO_CONTACT

async def auto_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["contact"] = update.message.text
    username = update.effective_user.username or "без username"

    msg = (
        f"\U0001F4CB *Запрос на расчет стоимости авто!*\n\n"
        f"\U0001F4DD Требования: {context.user_data['requirements']}\n"
        f"\U0001F4B0 Бюджет: {context.user_data['budget']}\n"
        f"\U0001F3D9\ufe0f Город: {context.user_data['city']}\n"
        f"\U0001F464 Имя: {context.user_data['name']}\n"
        f"\U0001F4DE Контакт: {context.user_data['contact']}\n"
        f"\U0001F517 Telegram: @{username}"
    )

    await notify_admins(context, escape_markdown(msg, version=2))
    await update.message.reply_text("Спасибо! Мы свяжемся с вами после расчета.")
    return ConversationHandler.END

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

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

if __name__ == "__main__":
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))

    application.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^request$")],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_contact)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    ))

    application.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^question$")],
        states={
            CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    ))

    application.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^feedback$")],
        states={
            CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_feedback)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    ))

    application.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^calculate$")],
        states={
            AUTO_REQUIREMENTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, auto_requirements)],
            AUTO_BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, auto_budget)],
            AUTO_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, auto_city)],
            AUTO_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, auto_name)],
            AUTO_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, auto_contact)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    ))

    print("Бот запущен.")
    application.run_polling()

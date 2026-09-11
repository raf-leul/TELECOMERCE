from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from bot.keyboards.menus import main_menu_keyboard

WELCOME_TEXT = (
    "Welcome to TeleCommerce! 🛍️\n\n"
    "Shop the same catalog as our website, right here in Telegram.\n"
    "Use the menu below to get started."
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME_TEXT, reply_markup=main_menu_keyboard())


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(WELCOME_TEXT, reply_markup=main_menu_keyboard())


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "Browse Products to see what's in stock, add items to your Cart, "
        "then check My Orders once you've placed an order on the website "
        "(Telegram account linking is coming in a future update).",
        reply_markup=main_menu_keyboard(),
    )

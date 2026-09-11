"""
Bot entrypoint. Uses polling for local development. Master instructions
section 16 recommends webhook-based deployment for production — that's
deferred here because it requires a real Telegram Bot API token (from
@BotFather) and a publicly reachable HTTPS URL, neither of which exist in
this development environment. See docs/DECISIONS.md and
docs/DEVELOPMENT_LOG.md for what has and hasn't been verified.
"""
from __future__ import annotations

import os

from telegram.ext import Application, CallbackQueryHandler, CommandHandler

from bot.handlers.cart import add_to_cart_callback, view_cart_callback
from bot.handlers.orders import checkout_callback, my_orders_callback
from bot.handlers.products import (
    browse_callback,
    category_selected_callback,
    product_selected_callback,
)
from bot.handlers.start import help_callback, main_menu_callback, start


def build_application() -> Application:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"))
    application.add_handler(CallbackQueryHandler(help_callback, pattern="^help$"))
    application.add_handler(CallbackQueryHandler(browse_callback, pattern="^browse$"))
    application.add_handler(
        CallbackQueryHandler(category_selected_callback, pattern="^category:")
    )
    application.add_handler(
        CallbackQueryHandler(product_selected_callback, pattern="^product:")
    )
    application.add_handler(CallbackQueryHandler(view_cart_callback, pattern="^view_cart$"))
    application.add_handler(
        CallbackQueryHandler(add_to_cart_callback, pattern="^add_to_cart:")
    )
    application.add_handler(CallbackQueryHandler(my_orders_callback, pattern="^my_orders$"))
    application.add_handler(CallbackQueryHandler(checkout_callback, pattern="^checkout$"))

    return application


def main() -> None:
    application = build_application()
    application.run_polling()


if __name__ == "__main__":
    main()

"""
Checkout (POST /orders) and order history (GET /orders) both require an
authenticated Supabase access token — see docs/DECISIONS.md, "checkout
requires authentication, guest checkout deferred". The bot has no way yet
to obtain one: Telegram-to-Supabase account linking is an explicitly
deferred feature (master instructions section 16 lists "account linking
where supported" as part of Stage 8's scope, but doing it properly is a
real design decision — how does a Telegram user prove they're also a
registered web user? — not a quick add alongside browsing/cart).

Both handlers below are honest placeholders: they tell the user exactly
what's missing rather than silently failing or pretending to check out.
"""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

ACCOUNT_LINKING_NOT_YET_AVAILABLE = (
    "Checking out and viewing order history from Telegram requires linking "
    "your Telegram account to your TeleCommerce account, which isn't built "
    "yet. For now, please complete your purchase on the website — your "
    "cart here in Telegram is separate from your web cart."
)


async def my_orders_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]]
    )
    await query.edit_message_text(ACCOUNT_LINKING_NOT_YET_AVAILABLE, reply_markup=keyboard)


async def checkout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ Back", callback_data="view_cart")]]
    )
    await query.edit_message_text(ACCOUNT_LINKING_NOT_YET_AVAILABLE, reply_markup=keyboard)

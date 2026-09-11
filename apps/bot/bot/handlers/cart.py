from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.services import api_client
from bot.services.identity import cart_token_for_telegram_user


def _format_cart(cart: dict) -> str:
    if not cart["items"]:
        return "Your cart is empty."

    lines = ["🛒 *Your Cart*\n"]
    for item in cart["items"]:
        price = item["unit_price_cents"] / 100
        line_total = item["line_total_cents"] / 100
        lines.append(f"{item['quantity']}x {item['name']} — ${price:.2f} each = ${line_total:.2f}")
    lines.append(f"\n*Subtotal: ${cart['subtotal_cents'] / 100:.2f}*")
    return "\n".join(lines)


async def view_cart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    cart_token = cart_token_for_telegram_user(update.effective_user.id)

    with api_client.make_api_client() as client:
        try:
            cart = api_client.get_cart(client, cart_token)
        except Exception:
            await query.edit_message_text(
                "Couldn't load your cart right now — please try again shortly."
            )
            return

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ Back", callback_data="main_menu")]]
    )
    await query.edit_message_text(
        _format_cart(cart), reply_markup=keyboard, parse_mode="Markdown"
    )


async def add_to_cart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    product_id = query.data.split(":", 1)[1]
    cart_token = cart_token_for_telegram_user(update.effective_user.id)

    with api_client.make_api_client() as client:
        try:
            cart = api_client.add_to_cart(client, cart_token, product_id, quantity=1)
        except Exception:
            await query.answer("Couldn't add that to your cart — please try again.", show_alert=True)
            return

    await query.answer(f"Added to cart! Subtotal: ${cart['subtotal_cents'] / 100:.2f}")

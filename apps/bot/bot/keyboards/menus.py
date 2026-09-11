from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🛍️ Browse Products", callback_data="browse")],
            [InlineKeyboardButton("🛒 Cart", callback_data="view_cart")],
            [InlineKeyboardButton("📦 My Orders", callback_data="my_orders")],
            [InlineKeyboardButton("❓ Help", callback_data="help")],
        ]
    )


def categories_keyboard(categories: list[dict]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(c["name"], callback_data=f"category:{c['id']}")]
        for c in categories
    ]
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def products_keyboard(products: list[dict]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(p["name"], callback_data=f"product:{p['slug']}")]
        for p in products
    ]
    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="browse")])
    return InlineKeyboardMarkup(buttons)


def product_detail_keyboard(product: dict) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "➕ Add to Cart", callback_data=f"add_to_cart:{product['id']}"
                )
            ],
            [InlineKeyboardButton("⬅️ Back", callback_data="browse")],
        ]
    )

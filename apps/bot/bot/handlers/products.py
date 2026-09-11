from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from bot.keyboards.menus import categories_keyboard, product_detail_keyboard, products_keyboard
from bot.services import api_client


async def browse_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    with api_client.make_api_client() as client:
        try:
            categories = api_client.list_categories(client)
        except Exception:
            await query.edit_message_text(
                "Couldn't load categories right now — please try again shortly."
            )
            return

    if not categories:
        await query.edit_message_text("No categories yet — check back soon!")
        return

    await query.edit_message_text(
        "Choose a category:", reply_markup=categories_keyboard(categories)
    )


async def category_selected_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    category_id = query.data.split(":", 1)[1]

    with api_client.make_api_client() as client:
        try:
            all_products = api_client.list_products(client)
        except Exception:
            await query.edit_message_text(
                "Couldn't load products right now — please try again shortly."
            )
            return

    products = [p for p in all_products if p.get("category_id") == category_id]

    if not products:
        await query.edit_message_text(
            "No products in this category yet.",
            reply_markup=products_keyboard([]),
        )
        return

    await query.edit_message_text(
        "Products in this category:", reply_markup=products_keyboard(products)
    )


async def product_selected_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    slug = query.data.split(":", 1)[1]

    with api_client.make_api_client() as client:
        try:
            product = api_client.get_product(client, slug)
        except Exception:
            await query.edit_message_text(
                "Couldn't load this product right now — please try again shortly."
            )
            return

    if product is None:
        await query.edit_message_text("This product is no longer available.")
        return

    price = product["price_cents"] / 100
    text = f"*{product['name']}*\n${price:.2f}\n\n{product.get('description') or ''}"
    await query.edit_message_text(
        text, reply_markup=product_detail_keyboard(product), parse_mode="Markdown"
    )

import asyncio
import json
import logging
import os
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = "8688478869:AAFRqPKq-_3dvfuXoyQztFQTztcHGtKvaS4"
ADMIN_ID = (5548318726, 1133070247)  # ЗАМЕНИ НА СВОЙ TELEGRAM USER ID
WEBAPP_URL = "https://onewix.github.io/catalog/"  # URL твоего веб-сервера (нужен HTTPS)

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ФАЙЛОВАЯ СИСТЕМА ---
def load_products():
    if not os.path.exists('products.json'):
        return []
    with open('products.json', 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_products(products):
    with open('products.json', 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=4)

# --- ХЭНДЛЕРЫ БОТА ---
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🛒 Открыть магазин", web_app=WebAppInfo(url=WEBAPP_URL))
    ]])
    await message.answer("Добро пожаловать в наш магазин! Нажми кнопку ниже, чтобы открыть каталог.", reply_markup=markup)

# --- ВЕБ-СЕРВЕР (API ДЛЯ MINI APP) ---
async def handle_index(request):
    return web.FileResponse('index.html')

async def api_get_products(request):
    return web.json_response(load_products())

async def api_save_product(request):
    data = await request.json()
    user_id = int(data.get('user_id', 0))
    if user_id != ADMIN_ID:
        return web.json_response({"error": "Forbidden"}, status=403)

    product = data.get('product')
    products = load_products()
    
    existing_idx = next((i for i, p in enumerate(products) if p['id'] == product['id']), None)
    if existing_idx is not None:
        products[existing_idx] = product
    else:
        products.append(product)
        
    save_products(products)
    return web.json_response({"status": "ok"})

async def api_delete_product(request):
    data = await request.json()
    user_id = int(data.get('user_id', 0))
    if user_id != ADMIN_ID:
        return web.json_response({"error": "Forbidden"}, status=403)

    prod_id = data.get('id')
    products = [p for p in load_products() if p['id'] != prod_id]
    save_products(products)
    return web.json_response({"status": "ok"})

async def api_place_order(request):
    data = await request.json()
    
    # Генерация номера заказа
    order_id = int(datetime.now().timestamp())
    
    username = data.get('username', 'Без username')
    fullname = data.get('fullname')
    phone = data.get('phone')
    address = data.get('address')
    items = data.get('items', [])
    total = data.get('total', 0)
    
    items_text = "\n".join([f"• {item['name']} - {item['qty']} шт. - {item['price'] * item['qty']} ₽" for item in items])
    
    order_text = (
        f"📦 <b>Новый заказ #{order_id}</b>\n\n"
        f"👤 <b>Username:</b> @{username}\n"
        f"📝 <b>ФИО:</b> {fullname}\n"
        f"📞 <b>Телефон:</b> {phone}\n"
        f"🏢 <b>Отделение почты:</b> {address}\n\n"
        f"🛒 <b>Список товаров:</b>\n{items_text}\n\n"
        f"💰 <b>Итоговая сумма:</b> {total} ₽"
    )
    
    # Сохранение в файл
    with open('orders.txt', 'a', encoding='utf-8') as f:
        f.write(order_text.replace('<b>', '').replace('</b>', '') + "\n" + "-"*30 + "\n")
    
    # Отправка админу
    try:
        await bot.send_message(chat_id=ADMIN_ID, text=order_text, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Не удалось отправить заказ админу: {e}")
        
    return web.json_response({"status": "ok", "order_id": order_id})

# --- ЗАПУСК ---
async def main():
    app = web.Application()
    app.router.add_get('/', handle_index)
    app.router.add_get('/api/products', api_get_products)
    app.router.add_post('/api/products', api_save_product)
    app.router.add_post('/api/products/delete', api_delete_product)
    app.router.add_post('/api/orders', api_place_order)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    
    logging.info("Веб-сервер запущен на порту 8080")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
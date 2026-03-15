import asyncio
import json
import logging
import os
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import hashlib
import hmac
import urllib.parse

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = "8688478869:AAFRqPKq-_3dvfuXoyQztFQTztcHGtKvaS4"
# Список ID администраторов — можно указывать несколько
ADMIN_IDS = (5548318726, 1133070247)
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


    # --- TELEGRAM WEBAPP init_data verification ---
    def verify_init_data(init_data: str) -> dict | None:
        """Verify Telegram Web App init_data string and return params dict if valid."""
        if not init_data:
            return None
        try:
            params = urllib.parse.parse_qs(init_data, keep_blank_values=True)
            # flatten values
            flat = {k: v[0] for k, v in params.items()}
            received_hash = flat.get('hash')
            if not received_hash:
                return None

            # build data_check_string from all fields except 'hash'
            items = []
            for k in sorted(flat.keys()):
                if k == 'hash':
                    continue
                items.append(f"{k}={flat[k]}")
            data_check_string = "\n".join(items)

            secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
            computed = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
            if computed != received_hash:
                return None

            return flat
        except Exception:
            return None

    def extract_user_id_from_init_data(init_data: str) -> int | None:
        params = verify_init_data(init_data)
        if not params:
            return None
        user_val = params.get('user')
        if not user_val:
            return None
        try:
            user_obj = json.loads(user_val)
            return int(user_obj.get('id', 0))
        except Exception:
            return None

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
    # Try to verify signed init_data first (preferred)
    user_id = None
    init_data = data.get('init_data')
    if init_data:
        try:
            verified = extract_user_id_from_init_data(init_data)
            if verified:
                user_id = verified
        except Exception:
            user_id = None

    if user_id is None:
        user_id = int(data.get('user_id', 0))

    if user_id not in ADMIN_IDS:
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
    # Verify init_data if provided
    user_id = None
    init_data = data.get('init_data')
    if init_data:
        try:
            verified = extract_user_id_from_init_data(init_data)
            if verified:
                user_id = verified
        except Exception:
            user_id = None

    if user_id is None:
        user_id = int(data.get('user_id', 0))

    if user_id not in ADMIN_IDS:
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

    # Try to get verified user id (optional) to include in order
    verified_user = None
    init_data = data.get('init_data')
    if init_data:
        try:
            verified_user = extract_user_id_from_init_data(init_data)
        except Exception:
            verified_user = None
    
    items_text = "\n".join([f"• {item['name']} - {item['qty']} шт. - {item['price'] * item['qty']} ₽" for item in items])
    
    order_text = (
        f"📦 <b>Новый заказ #{order_id}</b>\n\n"
        f"👤 <b>Username:</b> @{username}\n"
        + (f"🆔 <b>User ID:</b> {verified_user}\n" if verified_user else "")
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
        for admin in ADMIN_IDS:
            await bot.send_message(chat_id=admin, text=order_text, parse_mode="HTML")
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

import asyncio
import json
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup

API_TOKEN = 'ВАШ_ТОКЕН_БОТА'
ADMIN_IDS = [12345678]  # ЗАМЕНИТЕ НА ВАШ ID
WEBAPP_URL = 'https://your-github-username.github.io/your-repo/'

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

def load_products():
    try:
        with open('products.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_products(data):
    with open('products.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@dp.message(Command("start"))
async def start(message: types.Message):
    builder = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открыть магазин 🛍", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])
    await message.answer("Добро пожаловать в магазин!", reply_markup=builder)

@dp.message(F.web_app_data)
async def handle_webapp_data(message: types.Message):
    data = json.loads(message.web_app_data.data)
    
    # Обработка ЗАКАЗА
    if data['type'] == 'order':
        order_id = message.message_id
        user = data['user']
        items_str = "\n".join([f"- {i['name']} x{i['qty']} ({i['price']}₽)" for i in data['items']])
        
        order_text = (
            f"📦 НОВЫЙ ЗАКАЗ №{order_id}\n"
            f"👤 Покупатель: @{message.from_user.username}\n"
            f"📝 ФИО: {user['name']}\n"
            f"📞 Тел: {user['phone']}\n"
            f"📮 Почта: {user['address']}\n\n"
            f"🛒 Товары:\n{items_str}\n\n"
            f"💰 Итого: {data['total']}₽"
        )

        # Сохранение в файл
        with open('orders.txt', 'a', encoding='utf-8') as f:
            f.write(order_text + "\n" + "="*20 + "\n")

        # Уведомление админов
        for admin_id in ADMIN_IDS:
            await bot.send_message(admin_id, order_text)
        
        await message.answer("✅ Заказ оформлен! Мы свяжемся с вами.")

    # Обработка АДМИН-ДЕЙСТВИЙ (Обновление JSON)
    elif data['type'] == 'admin':
        if message.from_user.id not in ADMIN_IDS:
            return
            
        current_products = load_products()
        if data['action'] == 'add':
            current_products.append(data['data'])
        elif data['action'] == 'delete':
            current_products = [p for p in current_products if p['id'] != data['data']['id']]
        
        save_products(current_products)
        await message.answer("⚙️ Данные товаров обновлены.")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())

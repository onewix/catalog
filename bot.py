import asyncio
import json
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup

API_TOKEN = '8688478869:AAFRqPKq-_3dvfuXoyQztFQTztcHGtKvaS4'
ADMIN_IDS = [5548318726] # ТВОЙ ID
WEBAPP_URL = 'https://onewix.github.io/catalog/'

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

def load_products():
    try:
        with open('products.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except: return []

def save_products(data):
    with open('products.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@dp.message(Command("start"))
async def start(message: types.Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Начать покупки", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])
    await message.answer("Добро пожаловать в магазин!", reply_markup=markup)

@dp.message(F.web_app_data)
async def handle_data(message: types.Message):
    data = json.loads(message.web_app_data.data)
    
    if data['type'] == 'order':
        u = data['user']
        items = "\n".join([f"• {i['name']} x{i['qty']}" for i in data['items']])
        res = (f"🔥 НОВЫЙ ЗАКАЗ 🔥\n\n👤 Клиент: {u['name']}\n📞 Тел: {u['phone']}\n"
               f"📮 Почта: {u['address']}\n\n🛍 Товары:\n{items}\n\n💰 Итого: {data['total']}₽")
        
        with open('orders.txt', 'a', encoding='utf-8') as f:
            f.write(res + "\n---\n")
            
        for aid in ADMIN_IDS:
            await bot.send_message(aid, res)
        await message.answer("Заказ принят! Спасибо.")

    elif data['type'] == 'admin':
        if message.from_user.id in ADMIN_IDS:
            prods = load_products()
            prods.append(data['data'])
            save_products(prods)
            await message.answer("✅ Товар успешно добавлен в базу.")

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())

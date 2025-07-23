import asyncio
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
import aiosqlite
import os

API_TOKEN = os.getenv('API_TOKEN', '8085303818:AAE1G-ekS5pWFqdTIR0eibXCMoWYNs77RaU')  # Лучше задать через переменные окружения
CHANNEL_ID = os.getenv('CHANNEL_ID', '@your_channel_4')  # Лучше задать через переменные окружения
DB_PATH = "users.db"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
app = FastAPI()

# --- Inline Keyboards ---
def subscribe_inline_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Subscribe", url="https://t.me/your_channel_4")],
            [InlineKeyboardButton(text="Check", callback_data="check_sub")]
        ]
    )

def games_inline_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✈️ Lucky Jet", callback_data="game_LuckyJet"),
             InlineKeyboardButton(text="🛩 Aviator", callback_data="game_Aviator")],
            [InlineKeyboardButton(text="🪙 CoinFlip", callback_data="game_CoinFlip"),
             InlineKeyboardButton(text="💣 Mines", callback_data="game_Mines")],
            [InlineKeyboardButton(text="👑 Royal Mines", callback_data="game_RoyalMines"),
             InlineKeyboardButton(text="💵 Bombucks", callback_data="game_Bombucks")],
        ]
    )

def main_menu_inline_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Back to main menu", callback_data="main_menu")]
        ]
    )

def game_action_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Instruction", callback_data="instruction")],
            [InlineKeyboardButton(text="💥 Hack the game", callback_data="hack_game")],
            [InlineKeyboardButton(text="Back to main menu", callback_data="main_menu")],
        ]
    )

def hack_signal_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💡 Get signal", callback_data="get_signal")],
            [InlineKeyboardButton(text="Back to main menu", callback_data="main_menu")],
        ]
    )

# --- DB for postbacks only ---
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS postbacks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT,
                date TEXT,
                country TEXT,
                user_id TEXT,
                sub1 TEXT
            )
        ''')
        await db.commit()

# --- aiogram Handlers (no user DB) ---
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer("Subscribe to the channel and press 'Check'", reply_markup=subscribe_inline_kb())

@dp.callback_query(lambda c: c.data == "check_sub")
async def check_subscription(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    try:
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            await callback.message.delete()
            await callback.message.answer("Thank you for subscribing! Now choose a game to hack:", reply_markup=games_inline_kb())
        else:
            await callback.message.delete()
            await callback.message.answer(
                "You are not subscribed! Please subscribe and try again.",
                reply_markup=subscribe_inline_kb()
            )
    except TelegramBadRequest:
        await callback.message.delete()
        await callback.message.answer(
            "You are not subscribed! Please subscribe and try again.",
            reply_markup=subscribe_inline_kb()
        )
    except Exception as e:
        await callback.message.delete()
        await callback.message.answer("Subscription check error. Please try again later.")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("game_"))
async def choose_game(callback: types.CallbackQuery):
    game = callback.data.split('_', 1)[1]
    await callback.message.delete()
    await callback.message.answer(f"You selected: {game}", reply_markup=game_action_kb())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "instruction")
async def instruction(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("Video + game instruction.", reply_markup=main_menu_inline_kb())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "hack_game")
async def hack_game(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("Signal delivery / Launch Web App", reply_markup=hack_signal_kb())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "get_signal")
async def get_signal(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("Signals are now available! (+ photo)", reply_markup=main_menu_inline_kb())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "main_menu")
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("Main menu. Choose a game to hack:", reply_markup=games_inline_kb())
    await callback.answer()

# --- FastAPI endpoint for postbacks ---
@app.post("/postback")
async def postback(request: Request):
    data = await request.json()
    event_id = data.get("event_id")
    date = data.get("date")
    country = data.get("country")
    user_id = data.get("user_id")
    sub1 = data.get("sub1")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO postbacks (event_id, date, country, user_id, sub1) VALUES (?, ?, ?, ?, ?)",
            (event_id, date, country, user_id, sub1)
        )
        await db.commit()
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"status": "ok"}

@app.on_event("startup")
async def on_startup():
    await init_db()
    # aiogram polling запускается в отдельной задаче, не блокируя FastAPI
    asyncio.create_task(dp.start_polling(bot))

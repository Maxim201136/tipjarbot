import asyncio
import os
import json
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, PreCheckoutQuery,
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8992154556:AAGwXM5teGZN6YmPZMHRwqzX1AQ5YCahhbw")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
DATA_FILE = "data.json"

bot = Bot(BOT_TOKEN)
dp = Dispatcher()


# ---------- Простое хранилище (JSON вместо БД) ----------
def load_data():
    if os.path.exists(DATA_FILE):
        return json.load(open(DATA_FILE))
    return {"users": {}, "tips": []}

def save_data(data):
    json.dump(data, open(DATA_FILE, "w"), ensure_ascii=False, indent=2)


# ---------- Клавиатуры ----------
def main_kb(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Отправить донат 50⭐", callback_data="tip:50")],
        [InlineKeyboardButton(text="💎 Отправить донат 100⭐", callback_data="tip:100")],
        [InlineKeyboardButton(text="🚀 Отправить донат 500⭐", callback_data="tip:500")],
        [InlineKeyboardButton(text="📊 Моя статистика", callback_data="stats")],
    ])

def owner_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📈 Все донаты", callback_data="owner:all")],
        [InlineKeyboardButton(text="👥 Все юзеры", callback_data="owner:users")],
    ])


# ---------- Хэндлеры ----------
@dp.message(CommandStart())
async def start(msg: Message):
    data = load_data()
    uid = str(msg.from_user.id)
    if uid not in data["users"]:
        data["users"][uid] = {
            "name": msg.from_user.full_name,
            "username": msg.from_user.username or "",
            "total": 0,
        }
        save_data(data)
    await msg.answer(
        f"👋 Привет, {msg.from_user.first_name}!\n\n"
        "Я помогу тебе поддержать любимого автора.\n"
        "Выбери сумму доната:",
        reply_markup=main_kb(msg.from_user.id),
    )


@dp.callback_query(F.data.startswith("tip:"))
async def tip(cb: CallbackQuery):
    amount = int(cb.data.split(":")[1])
    await bot.send_invoice(
        chat_id=cb.from_user.id,
        title=f"Донат {amount}⭐",
        description="Поддержка автора через Telegram Stars",
        payload=f"tip_{amount}",
        currency="XTR",
        prices=[LabeledPrice(label="Донат", amount=amount)],
        provider_token="",
    )
    await cb.answer()


@dp.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    await q.answer(ok=True)


@dp.message(F.successful_payment)
async def paid(msg: Message):
    amount = msg.successful_payment.total_amount
    data = load_data()
    uid = str(msg.from_user.id)
    data["users"][uid]["total"] = data["users"][uid].get("total", 0) + amount
    data["tips"].append({
        "user_id": uid,
        "name": msg.from_user.full_name,
        "amount": amount,
    })
    save_data(data)

    await msg.answer(f"🎉 Спасибо за донат {amount}⭐! Автор получит уведомление.")

    # Уведомляем владельца
    if OWNER_ID:
        total = sum(t["amount"] for t in data["tips"])
        try:
            await bot.send_message(
                OWNER_ID,
                f"💰 Новый донат!\n"
                f"От: {msg.from_user.full_name} (@{msg.from_user.username})\n"
                f"Сумма: {amount}⭐\n"
                f"Всего собрано: {total}⭐"
            )
        except Exception:
            pass


@dp.callback_query(F.data == "stats")
async def stats(cb: CallbackQuery):
    data = load_data()
    uid = str(cb.from_user.id)
    user = data["users"].get(uid, {})
    total_tips = sum(t["amount"] for t in data["tips"])
    await cb.message.answer(
        f"📊 Твоя статистика:\n\n"
        f"Ты задонатил: {user.get('total', 0)}⭐\n"
        f"Всего в системе: {total_tips}⭐\n"
        f"Донатов сделано: {len(data['tips'])}"
    )
    await cb.answer()


@dp.message(Command("admin"))
async def admin(msg: Message):
    if msg.from_user.id != OWNER_ID:
        return
    data = load_data()
    total = sum(t["amount"] for t in data["tips"])
    await msg.answer(
        f"🔧 Админ-панель\n\n"
        f"Юзеров: {len(data['users'])}\n"
        f"Донатов: {len(data['tips'])}\n"
        f"Собрано: {total}⭐",
        reply_markup=owner_kb(),
    )


@dp.callback_query(F.data == "owner:all")
async def owner_all(cb: CallbackQuery):
    if cb.from_user.id != OWNER_ID:
        return
    data = load_data()
    if not data["tips"]:
        await cb.message.answer("Пока нет донатов")
    else:
        last = data["tips"][-10:]
        text = "\n".join(f"• {t['name']}: {t['amount']}⭐" for t in last)
        await cb.message.answer(f"Последние 10 донатов:\n{text}")
    await cb.answer()


@dp.callback_query(F.data == "owner:users")
async def owner_users(cb: CallbackQuery):
    if cb.from_user.id != OWNER_ID:
        return
    data = load_data()
    text = "\n".join(
        f"• {u['name']} — {u.get('total', 0)}⭐"
        for u in data["users"].values()
    )
    await cb.message.answer(f"Юзеры ({len(data['users'])}):\n{text or 'пусто'}")
    await cb.answer()


# ---------- Запуск ----------
async def main():
    print("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

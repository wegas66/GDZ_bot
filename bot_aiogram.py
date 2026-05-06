import asyncio
import base64
import json
from os import getenv

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from config import TELEGRAM_TOKEN, MINI_APP_URL
from logger import logger
from utils import solve_text, solve_image, transcribe_voice

dp = Dispatcher()

async def processing_message(message: Message, text: str):
    return await message.reply(text)

def make_webapp_button(solution: dict) -> InlineKeyboardMarkup:
    """Create 'Открыть решение' button with solution data encoded in URL."""
    # Pass data as URL fragment so it never hits the server
    payload = base64.urlsafe_b64encode(
        json.dumps(solution, ensure_ascii=False).encode()
    ).decode()
    url = f"{MINI_APP_URL}?data={payload}"
    return InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text="📖 Открыть решение",
                    web_app=WebAppInfo(url=url)
                )
            ]]
        )

@dp.message(Command("start"))
async def command_start_handler(message: Message) -> None:
    await message.reply(
        text="👋 Привет! Я помогу решить домашнее задание.\n\n"
        "Просто отправь мне:\n"
        "📷 *Фото* с задачей\n"
        "✍️ *Текст* задачи\n"
        "🎤 *Голосовое* сообщение\n\n"
        "Я решу и покажу пошаговое решение!",
        parse_mode="Markdown")

@dp.message(F.text & ~F.command)
async def handle_text(message: Message) -> None:
    msg = await processing_message(message, "⏳ Решаю задачу…")
    try:
        solution = await solve_text(message.text)
        if "error" in solution:
            await msg.edit_text(f"❌ {solution['error']}")
            return
        await msg.edit_text(
            f"✅ *{solution.get('subject','Решение')}* — {solution.get('title','')}",
            reply_markup=make_webapp_button(solution),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.exception("text handler error")
        await msg.edit_text("❌ Ошибка при решении. Попробуй ещё раз.")

@dp.message(F.photo)
async def handle_photo(message: Message, bot: Bot):
    msg = await processing_message(message, "📷 Читаю фото…")
    try:
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        file_bytes = await bot.download_file(file.file_path)
        image_bytes = file_bytes.read()

        await msg.edit_text("⏳ Решаю задачу с фото…")
        solution = await solve_image(image_bytes)

        if "error" in solution:
            await msg.edit_text(f"❌ {solution['error']}")
            return
        await msg.edit_text(
            text=f"✅ *{solution.get('subject','Решение')}* — {solution.get('title','')}",
            reply_markup=make_webapp_button(solution),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.exception("photo handler error")
        await msg.edit_text("❌ Ошибка при обработке фото.")

@dp.message(F.voice)
async def handle_voice(message: Message, bot: Bot):
    msg = await processing_message(message, "🎤 Распознаю речь…")
    try:
        voice = message.voice
        file = await bot.get_file(voice.file_id)
        file_bytes = await bot.download_file(file.file_path)
        ogg_bytes = file_bytes.read()

        text = await transcribe_voice(ogg_bytes)
        await msg.edit_text(f"🗣 Распознано: _{text}_\n\n⏳ Решаю…")

        solution = await solve_text(text)
        if "error" in solution:
            await msg.edit_text(f"❌ {solution['error']}")
            return
        await msg.edit_text(
            text=f"✅ *{solution.get('subject','Решение')}* — {solution.get('title','')}",
            reply_markup=make_webapp_button(solution),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.exception("voice handler error")
        await msg.edit_text("❌ Ошибка при обработке голосового.")

@dp.message(F.document)
async def handle_document(message: Message, bot: Bot):
    """Handle photos sent as files (documents)."""
    doc = message.document
    if doc.mime_type and doc.mime_type.startswith("image/"):
        msg = await processing_message(message, "📄 Читаю файл…")
        try:
            file = await bot.get_file(doc.file_id)
            file_bytes = await bot.download_file(file.file_path)
            doc_bytes = file_bytes.read()
            solution = await solve_image(doc_bytes, mime=doc.mime_type)
            if "error" in solution:
                await msg.edit_text(f"❌ {solution['error']}")
                return
            await msg.edit_text(
                text=f"✅ *{solution.get('subject','Решение')}* — {solution.get('title','')}",
                reply_markup=make_webapp_button(solution),
                parse_mode="Markdown"
            )
        except Exception:
            logger.exception("document handler error")
            await msg.edit_text("❌ Ошибка при обработке файла.")
    else:
        await message.reply("Отправь фото, текст или голосовое сообщение с задачей.")

# Run the bot
async def main() -> None:
    bot = Bot(token=TELEGRAM_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
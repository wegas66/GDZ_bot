import os
import logging
import base64
import json
import asyncio
from pathlib import Path

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)
import openai
import httpx

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
MINI_APP_URL   = os.environ["MINI_APP_URL"]   # e.g. https://yourdomain.com/miniapp/

openai_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Ты — умный помощник по домашним заданиям (ГДЗ).
Твоя задача — дать ПОЛНОЕ и ПОНЯТНОЕ решение задачи.

Правила форматирования ответа (строго!):
1. Верни ТОЛЬКО валидный JSON без markdown-обёртки.
2. Структура JSON:
{
  "subject": "Название предмета (Математика / Физика / Химия / и т.д.)",
  "title": "Краткое описание задачи (1 строка)",
  "steps": [
    {"n": 1, "text": "Шаг 1 с объяснением", "formula": "LaTeX формула если нужна или null"},
    ...
  ],
  "answer": "Финальный ответ",
  "hint": "Краткая подсказка / совет для запоминания"
}
3. Формулы пиши в LaTeX без $$ — просто выражение, например: x = \\frac{-b}{2a}
4. Если задача не из учёбы — верни {"error": "Это не похоже на учебное задание."}
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

async def solve_text(text: str) -> dict:
    """Send text task to GPT-4o and return parsed JSON solution."""
    resp = await openai_client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        max_tokens=2000,
    )
    return json.loads(resp.choices[0].message.content)


async def solve_image(image_bytes: bytes, mime: str = "image/jpeg") -> dict:
    """Send image to GPT-4o Vision."""
    b64 = base64.b64encode(image_bytes).decode()
    resp = await openai_client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    },
                    {"type": "text", "text": "Реши задачу с фото."},
                ],
            },
        ],
        max_tokens=2000,
    )
    return json.loads(resp.choices[0].message.content)


async def transcribe_voice(ogg_bytes: bytes) -> str:
    """Transcribe Telegram voice message (ogg/opus) via Whisper."""
    import io
    audio_file = io.BytesIO(ogg_bytes)
    audio_file.name = "voice.ogg"
    transcript = await openai_client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        language="ru",
    )
    return transcript.text


def make_webapp_button(solution: dict) -> InlineKeyboardMarkup:
    """Create 'Открыть решение' button with solution data encoded in URL."""
    # Pass data as URL fragment so it never hits the server
    payload = base64.urlsafe_b64encode(
        json.dumps(solution, ensure_ascii=False).encode()
    ).decode()
    url = f"{MINI_APP_URL}?data={payload}"
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("📖 Открыть решение", web_app=WebAppInfo(url=url))]]
    )


async def processing_message(update: Update, text: str):
    return await update.message.reply_text(text, parse_mode=None)


# ── Handlers ──────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я помогу решить домашнее задание.\n\n"
        "Просто отправь мне:\n"
        "📷 *Фото* с задачей\n"
        "✍️ *Текст* задачи\n"
        "🎤 *Голосовое* сообщение\n\n"
        "Я решу и покажу пошаговое решение!",
        parse_mode="Markdown",
    )


async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = await processing_message(update, "⏳ Решаю задачу…")
    try:
        solution = await solve_text(update.message.text)
        if "error" in solution:
            await msg.edit_text(f"❌ {solution['error']}")
            return
        await msg.edit_text(
            f"✅ *{solution.get('subject','Решение')}* — {solution.get('title','')}",
            parse_mode="Markdown",
            reply_markup=make_webapp_button(solution),
        )
    except Exception as e:
        logger.exception("text handler error")
        await msg.edit_text("❌ Ошибка при решении. Попробуй ещё раз.")


async def handle_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = await processing_message(update, "📷 Читаю фото…")
    try:
        photo = update.message.photo[-1]           # highest resolution
        file = await ctx.bot.get_file(photo.file_id)
        async with httpx.AsyncClient() as client:
            r = await client.get(file.file_path)
        image_bytes = r.content

        await msg.edit_text("⏳ Решаю задачу с фото…")
        solution = await solve_image(image_bytes)

        if "error" in solution:
            await msg.edit_text(f"❌ {solution['error']}")
            return
        await msg.edit_text(
            f"✅ *{solution.get('subject','Решение')}* — {solution.get('title','')}",
            parse_mode="Markdown",
            reply_markup=make_webapp_button(solution),
        )
    except Exception as e:
        logger.exception("photo handler error")
        await msg.edit_text("❌ Ошибка при обработке фото.")


async def handle_voice(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = await processing_message(update, "🎤 Распознаю речь…")
    try:
        voice = update.message.voice
        file = await ctx.bot.get_file(voice.file_id)
        async with httpx.AsyncClient() as client:
            r = await client.get(file.file_path)
        ogg_bytes = r.content

        text = await transcribe_voice(ogg_bytes)
        await msg.edit_text(f"🗣 Распознано: _{text}_\n\n⏳ Решаю…", parse_mode="Markdown")

        solution = await solve_text(text)
        if "error" in solution:
            await msg.edit_text(f"❌ {solution['error']}")
            return
        await msg.edit_text(
            f"✅ *{solution.get('subject','Решение')}* — {solution.get('title','')}",
            parse_mode="Markdown",
            reply_markup=make_webapp_button(solution),
        )
    except Exception as e:
        logger.exception("voice handler error")
        await msg.edit_text("❌ Ошибка при обработке голосового.")


async def handle_document(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Handle photos sent as files (documents)."""
    doc = update.message.document
    if doc.mime_type and doc.mime_type.startswith("image/"):
        msg = await processing_message(update, "📄 Читаю файл…")
        try:
            file = await ctx.bot.get_file(doc.file_id)
            async with httpx.AsyncClient() as client:
                r = await client.get(file.file_path)
            solution = await solve_image(r.content, mime=doc.mime_type)
            if "error" in solution:
                await msg.edit_text(f"❌ {solution['error']}")
                return
            await msg.edit_text(
                f"✅ *{solution.get('subject','Решение')}* — {solution.get('title','')}",
                parse_mode="Markdown",
                reply_markup=make_webapp_button(solution),
            )
        except Exception:
            logger.exception("document handler error")
            await msg.edit_text("❌ Ошибка при обработке файла.")
    else:
        await update.message.reply_text("Отправь фото, текст или голосовое сообщение с задачей.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot started. Polling…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

import base64
import json

from config import openai_client, MINI_APP_URL

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
    """Send text task to GPT-5.2 and return parsed JSON solution."""
    resp = await openai_client.chat.completions.create(
        model="gpt-5.2",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
    )
    return json.loads(resp.choices[0].message.content)


async def solve_image(image_bytes: bytes, mime: str = "image/jpeg") -> dict:
    """Send image to GPT-5.2 Vision."""
    b64 = base64.b64encode(image_bytes).decode()
    resp = await openai_client.chat.completions.create(
        model="gpt-5.2",
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
    )
    return json.loads(resp.choices[0].message.content)


async def transcribe_voice(ogg_bytes: bytes) -> str:
    """Transcribe Telegram voice message (ogg/opus) via Whisper."""
    import io
    audio_file = io.BytesIO(ogg_bytes)
    audio_file.name = "voice.ogg"
    transcript = await openai_client.audio.transcriptions.create(
        model="gpt-4o-transcribe",
        file=audio_file,
        language="ru",
    )
    return transcript.text

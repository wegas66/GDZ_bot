# 📚 ГДЗ Telegram Bot

Бот решает домашние задания по фото, тексту и голосовым сообщениям.  
Решение отображается в красивом **Telegram Mini App** с пошаговым объяснением и формулами.

---

## 🏗 Архитектура

```
Пользователь → Telegram Bot (Python)
                    ↓
              OpenAI GPT-4o / Whisper
                    ↓
              JSON с решением
                    ↓ (кодируется в URL)
              Telegram Mini App (HTML + KaTeX)
```

---

## ⚡ Быстрый старт (Docker)

### 1. Создай бота в @BotFather

```
/newbot → получи TELEGRAM_BOT_TOKEN
```

### 2. Получи OpenAI API ключ

https://platform.openai.com/api-keys

### 3. Разверни Mini App (нужен HTTPS!)

Telegram требует **HTTPS** для Mini App.  
Варианты:
- VPS + домен + Let's Encrypt (Certbot)
- [Railway](https://railway.app) / [Render](https://render.com) — бесплатно
- [Cloudflare Pages](https://pages.cloudflare.com) — папку `miniapp/` залить как статику

### 4. Настрой переменные

```bash
cp .env.example .env
nano .env   # заполни все три значения
```

### 5. Зарегистрируй Mini App в BotFather

```
/mybots → выбери бота → Bot Settings → Menu Button
→ укажи URL: https://yourdomain.com/
→ Text: 📖 Решения
```

### 6. Запусти

```bash
docker compose up -d
```

---

## 🖥 Локальная разработка (без Docker)

```bash
cd bot
pip install -r requirements.txt

export TELEGRAM_BOT_TOKEN="..."
export OPENAI_API_KEY="..."
export MINI_APP_URL="https://yourdomain.com/"

python bot.py
```

Для Mini App во время разработки можно использовать [ngrok](https://ngrok.com/):
```bash
ngrok http 8080
# Запусти любой статический сервер на порту 8080:
cd miniapp && python -m http.server 8080
```

---

## 📁 Структура проекта

```
gdzbot/
├── bot/
│   ├── bot.py            # Telegram bot (python-telegram-bot)
│   ├── requirements.txt
│   └── Dockerfile
├── miniapp/
│   └── index.html        # Telegram Mini App (KaTeX, pure HTML)
├── docker-compose.yml
├── nginx.conf
└── .env.example
```

---

## 🎨 Что умеет Mini App

- Красивая тёмная тема
- Цвет акцента меняется по предмету (матем, физика, химия…)
- **Пошаговое решение** с анимацией появления
- **Формулы LaTeX** через KaTeX
- **Ответ** и **подсказка** для запоминания
- Адаптивный (мобайл-первый)

---

## 🔧 Поддерживаемые форматы входных данных

| Формат | Описание |
|--------|----------|
| 📷 Фото | Скан/фото задачи (JPG, PNG) |
| 📄 Файл | Изображение отправленное как файл |
| ✍️ Текст | Задача набранная вручную |
| 🎤 Голос | Продиктованная задача (Whisper STT) |

---

## 💰 Примерная стоимость

| Запрос | Модель | ~цена |
|--------|--------|-------|
| Текст | GPT-4o | ~$0.002 |
| Фото | GPT-4o Vision | ~$0.005 |
| Голос | Whisper-1 | ~$0.001 |

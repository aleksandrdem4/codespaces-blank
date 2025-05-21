import asyncio
import logging
import json
import requests
from gtts import gTTS
from pydub import AudioSegment
from pathlib import Path
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile

# === НАСТРОЙКИ ===
TELEGRAM_TOKEN = '7726016785:AAF8qdSCYX-CvVbr1oxqM2bxVuJp9bWYvzg'
OPENROUTER_API_KEY = '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'
OPENROUTER_MODEL = 'deepseek/deepseek-chat:free'

bot = Bot(
    token=TELEGRAM_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())

# === ОБРАБОТЧИК /start ===
@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    await message.answer("Привет! Напиши сообщение, и я спрошу у нейросети 🤖")

# === ОБРАБОТЧИК СООБЩЕНИЙ ===
@dp.message()
async def handle_message(message: types.Message):
    loading = await message.answer("Генерирую ответ...")
    user_text = message.text
    reply = await generate_ai_response(user_text)

    await bot.delete_message(message.chat.id, loading.message_id)
    await message.answer(reply)

    # === Генерация озвучки и отправка голосом ===
    audio_path = generate_tts(reply)
    if audio_path and Path(audio_path).exists():
        try:
            voice = FSInputFile(audio_path)
            await message.answer_voice(voice=voice)
            Path(audio_path).unlink(missing_ok=True)
        except Exception as e:
            await message.answer(f"⚠️ Ошибка при отправке голосового ответа:\n{e}")
    else:
        await message.answer("⚠️ Не удалось сгенерировать озвучку.")

# === ГЕНЕРАЦИЯ ОТВЕТА ОТ OPENROUTER ===
async def generate_ai_response(user_message: str) -> str:
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            data=json.dumps({
                "model": OPENROUTER_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "Ты — помощник, основанный на модели deepseek-chat. Не называй себя GPT и не говори, что ты от OpenAI."
                    },
                    {
                        "role": "user",
                        "content": user_message
                    }
                ]
            })
        )
        if response.status_code == 200:
            data = response.json()
            return data["choices"][0]["message"]["content"]
        else:
            return f"❌ Ошибка OpenRouter ({response.status_code}):\n{response.text}"
    except Exception as e:
        return f"⚠️ Ошибка при обращении к ИИ: {e}"

# === ГЕНЕРАЦИЯ И ОЗВУЧКА ТЕКСТА ===
def generate_tts(text: str) -> str:
    try:
        tts = gTTS(text=text[:1000], lang="ru")  # ограничим длину
        mp3_path = "response.mp3"
        ogg_path = "response.ogg"

        tts.save(mp3_path)

        sound = AudioSegment.from_mp3(mp3_path)
        sound.export(ogg_path, format="ogg", codec="libopus")

        Path(mp3_path).unlink(missing_ok=True)
        return ogg_path
    except Exception as e:
        print(f"[TTS ERROR] {e}")
        return None

# === ЗАПУСК ===
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import json
import os
import random
import string
from datetime import datetime, timedelta, timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
Application,
CallbackQueryHandler,
CommandHandler,
ContextTypes,
MessageHandler,
filters,
)

TOKEN_FILE = "config.txt"
CODES_FILE = "codes.txt"
USED_CODES_FILE = "used_codes.txt"
STATE_FILE = "state.json"

ACCESS_DURATION = timedelta(hours=24)
CHECK_INTERVAL = 30

SCENE_TEXTS = {
1: "СЦЕНА 1\n\nЗдесь находится текст первой сцены.",
2: "СЦЕНА 2\n\nЗдесь находится текст второй сцены.",
3: "СЦЕНА 3\n\nЗдесь находится текст третьей сцены.",
4: "СЦЕНА 4\n\nЗдесь находится текст четвёртой сцены.",
5: "СЦЕНА 5\n\nЗдесь находится текст пятой сцены.",
6: "СЦЕНА 6\n\nЗдесь находится текст шестой сцены.",
7: "СЦЕНА 7\n\nЗдесь находится текст седьмой сцены.",
8: "СЦЕНА 8\n\nЗдесь находится текст восьмой сцены.",
9: "СЦЕНА 9\n\nЗдесь находится текст девятой сцены.",
10: "СЦЕНА 10\n\nЗдесь находится текст десятой сцены.",
11: "СЦЕНА 11\n\nЗдесь находится текст одиннадцатой сцены.",
}

def read_token():
if not os.path.exists(TOKEN_FILE):
raise FileNotFoundError(
f"Файл {TOKEN_FILE} не найден."
)

```
with open(TOKEN_FILE, "r", encoding="utf-8") as file:
    content = file.read().strip()

if "=" in content:
    key, value = content.split("=", 1)

    if key.strip().upper() in ("BOT_TOKEN", "TOKEN"):
        content = value.strip()

if not content:
    raise ValueError(
        f"Файл {TOKEN_FILE} пустой."
    )

return content
```

def read_codes():
if not os.path.exists(CODES_FILE):
open(CODES_FILE, "a", encoding="utf-8").close()

```
with open(CODES_FILE, "r", encoding="utf-8") as file:
    return {
        line.strip()
        for line in file
        if line.strip()
    }
```

def read_used_codes():
if not os.path.exists(USED_CODES_FILE):
open(USED_CODES_FILE, "a", encoding="utf-8").close()

```
with open(USED_CODES_FILE, "r", encoding="utf-8") as file:
    return {
        line.strip()
        for line in file
        if line.strip()
    }
```

def mark_code_as_used(code):
with open(USED_CODES_FILE, "a", encoding="utf-8") as file:
file.write(code + "\n")

def load_state():
if not os.path.exists(STATE_FILE):
return {}

```
try:
    with open(STATE_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict):
        return data

except (json.JSONDecodeError, OSError):
    pass

return {}
```

def save_state(state):
temp_file = STATE_FILE + ".tmp"

```
with open(temp_file, "w", encoding="utf-8") as file:
    json.dump(
        state,
        file,
        ensure_ascii=False,
        indent=2
    )

os.replace(temp_file, STATE_FILE)
```

def generate_promo_code():
characters = string.ascii_uppercase + string.digits

```
random_part = "".join(
    random.choice(characters)
    for _ in range(5)
)

return f"GRAMADO-{random_part}"
```

def get_user_data(state, user_id):
return state.get(str(user_id))

def access_is_active(user_data):
if not user_data:
return False

```
expires_at = user_data.get("expires_at")

if not expires_at:
    return False

try:
    expiration = datetime.fromisoformat(expires_at)

    if expiration.tzinfo is None:
        expiration = expiration.replace(
            tzinfo=timezone.utc
        )

    return datetime.now(timezone.utc) < expiration

except ValueError:
    return False
```

def start_button():
keyboard = [
[
InlineKeyboardButton(
"НАЧАТЬ 🎧",
callback_data="start_scenes"
)
]
]

```
return InlineKeyboardMarkup(keyboard)
```

def next_scene_button(scene_number):
keyboard = [
[
InlineKeyboardButton(
"СЛЕДУЮЩАЯ СЦЕНА →",
callback_data=f"scene_{scene_number + 1}"
)
]
]

```
return InlineKeyboardMarkup(keyboard)
```

def finish_button():
keyboard = [
[
InlineKeyboardButton(
"СНЯТЬ НАУШНИКИ ✓",
callback_data="finish"
)
]
]

```
return InlineKeyboardMarkup(keyboard)
```

async def start(
update: Update,
context: ContextTypes.DEFAULT_TYPE
):
user = update.effective_user
user_id = user.id

```
state = context.application.bot_data["state"]

user_data = get_user_data(
    state,
    user_id
)

if access_is_active(user_data):
    await update.message.reply_text(
        "У вас уже есть активный доступ.\n\n"
        "Нажмите кнопку ниже, чтобы начать.",
        reply_markup=start_button()
    )
    return

context.user_data["waiting_for_code"] = True

await update.message.reply_text(
    "Введите ваш код доступа:"
)
```

async def check_code(
update: Update,
context: ContextTypes.DEFAULT_TYPE
):
if not update.message or not update.message.text:
return

```
user = update.effective_user
user_id = user.id
entered_code = update.message.text.strip()

if not context.user_data.get(
    "waiting_for_code"
):
    return

codes = read_codes()
used_codes = read_used_codes()

if entered_code not in codes:
    await update.message.reply_text(
        "❌ Неверный код.\n\n"
        "Проверьте код и попробуйте ещё раз."
    )
    return

if entered_code in used_codes:
    await update.message.reply_text(
        "❌ Этот код уже был использован."
    )
    return

mark_code_as_used(entered_code)

now = datetime.now(timezone.utc)
expires_at = now + ACCESS_DURATION

state = context.application.bot_data["state"]

promo_code = generate_promo_code()

state[str(user_id)] = {
    "code": entered_code,
    "activated_at": now.isoformat(),
    "expires_at": expires_at.isoformat(),
    "scene": 0,
    "finished": False,
    "promo_code": promo_code,
    "promo_sent": False,
}

save_state(state)

context.user_data["waiting_for_code"] = False

await update.message.reply_text(
    "✅ Код принят!\n\n"
    "Доступ активирован на 24 часа.\n\n"
    "Когда будете готовы, нажмите «НАЧАТЬ 🎧».",
    reply_markup=start_button()
)
```

async def start_scenes(
update: Update,
context: ContextTypes.DEFAULT_TYPE
):
query = update.callback_query

```
await query.answer()

user_id = query.from_user.id

state = context.application.bot_data["state"]

user_data = get_user_data(
    state,
    user_id
)

if not access_is_active(user_data):
    await query.message.reply_text(
        "⏰ Ваш доступ истёк."
    )
    return

user_data["scene"] = 1

save_state(state)

await send_scene(
    query.message,
    context,
    user_id,
    1
)
```

async def send_scene(
message,
context,
user_id,
scene_number
):
state = context.application.bot_data["state"]

```
user_data = get_user_data(
    state,
    user_id
)

if not access_is_active(user_data):
    await message.reply_text(
        "⏰ Ваш доступ истёк."
    )
    return

if scene_number < 1 or scene_number > 11:
    return

audio_filename = f"scena{scene_number}.mp3"

if not os.path.exists(audio_filename):
    await message.reply_text(
        f"❌ Не найден аудиофайл "
        f"{audio_filename}."
    )
    return

scene_text = SCENE_TEXTS.get(
    scene_number,
    f"СЦЕНА {scene_number}"
)

with open(
    audio_filename,
    "rb"
) as audio:

    await message.reply_audio(
        audio=audio,
        title=f"Сцена {scene_number}",
        performer="Ваш бот"
    )

if scene_number < 11:

    await message.reply_text(
        scene_text,
        reply_markup=next_scene_button(
            scene_number
        )
    )

else:

    await message.reply_text(
        scene_text,
        reply_markup=finish_button()
    )
```

async def next_scene(
update: Update,
context: ContextTypes.DEFAULT_TYPE
):
query = update.callback_query

```
await query.answer()

user_id = query.from_user.id

state = context.application.bot_data["state"]

user_data = get_user_data(
    state,
    user_id
)

if not access_is_active(user_data):
    await query.message.reply_text(
        "⏰ Ваш доступ истёк."
    )
    return

try:
    scene_number = int(
        query.data.replace(
            "scene_",
            ""
        )
    )

except ValueError:
    return

if scene_number < 1 or scene_number > 11:
    return

user_data["scene"] = scene_number

save_state(state)

await send_scene(
    query.message,
    context,
    user_id,
    scene_number
)
```

async def finish(
update: Update,
context: ContextTypes.DEFAULT_TYPE
):
query = update.callback_query

```
await query.answer()

user_id = query.from_user.id

state = context.application.bot_data["state"]

user_data = get_user_data(
    state,
    user_id
)

if not access_is_active(user_data):
    await query.message.reply_text(
        "⏰ Ваш доступ истёк."
    )
    return

user_data["finished"] = True

save_state(state)

promo_code = user_data.get(
    "promo_code"
)

await query.message.reply_text(
    "🎉 Вы завершили все 11 сцен!\n\n"
    "Ваш промокод:\n\n"
    f"🎁 {promo_code}\n\n"
    "Сохраните его — он может вам понадобиться."
)
```

async def expiration_worker(application):
while True:

```
    try:
        await asyncio.sleep(
            CHECK_INTERVAL
        )

        state = application.bot_data["state"]

        changed = False

        now = datetime.now(
            timezone.utc
        )

        for user_id, user_data in list(
            state.items()
        ):

            if user_data.get(
                "promo_sent"
            ):
                continue

            expires_at_string = user_data.get(
                "expires_at"
            )

            if not expires_at_string:
                continue

            try:
                expires_at = datetime.fromisoformat(
                    expires_at_string
                )

                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(
                        tzinfo=timezone.utc
                    )

            except ValueError:
                continue

            if now >= expires_at:

                promo_code = user_data.get(
                    "promo_code"
                )

                if not promo_code:
                    promo_code = generate_promo_code()

                    user_data[
                        "promo_code"
                    ] = promo_code

                try:

                    await application.bot.send_message(
                        chat_id=int(user_id),
                        text=(
                            "⏰ Ваши 24 часа "
                            "доступа закончились.\n\n"
                            "Спасибо за прохождение!\n\n"
                            "Ваш промокод:\n\n"
                            f"🎁 {promo_code}"
                        )
                    )

                    user_data[
                        "promo_sent"
                    ] = True

                    changed = True

                except Exception as error:

                    print(
                        "Ошибка отправки сообщения "
                        f"user_id={user_id}: {error}"
                    )

        if changed:
            save_state(state)

    except asyncio.CancelledError:
        break

    except Exception as error:

        print(
            f"Ошибка expiration_worker: {error}"
        )
```

async def post_init(application):

```
application.bot_data[
    "expiration_task"
] = asyncio.create_task(
    expiration_worker(application)
)
```

async def post_shutdown(application):

```
task = application.bot_data.get(
    "expiration_task"
)

if task:

    task.cancel()

    try:
        await task

    except asyncio.CancelledError:
        pass
```

async def error_handler(
update: object,
context: ContextTypes.DEFAULT_TYPE
):

```
print(
    "Ошибка при обработке обновления: "
    f"{context.error}"
)
```

def main():

```
token = read_token()

state = load_state()

application = (
    Application.builder()
    .token(token)
    .post_init(post_init)
    .post_shutdown(post_shutdown)
    .build()
)

application.bot_data[
    "state"
] = state

application.add_handler(
    CommandHandler(
        "start",
        start
    )
)

application.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        check_code
    )
)

application.add_handler(
    CallbackQueryHandler(
        start_scenes,
        pattern=r"^start_scenes$"
    )
)

application.add_handler(
    CallbackQueryHandler(
        next_scene,
        pattern=r"^scene_(?:[1-9]|10|11)$"
    )
)

application.add_handler(
    CallbackQueryHandler(
        finish,
        pattern=r"^finish$"
    )
)

application.add_error_handler(
    error_handler
)

print("Бот запущен.")

application.run_polling(
    drop_pending_updates=True
)
```

if **name** == "**main**":
main()

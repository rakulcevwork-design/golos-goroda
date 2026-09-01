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
AUDIO_FOLDER = "audio"

ACCESS_DURATION = timedelta(hours=24)
CHECK_INTERVAL = 30

SCENE_TEXTS = {
    1: "🎧 Сцена 1 — Фонтан любви\n\nВы стоите у Фонтана любви рядом с Igreja São Pedro.\n\nПосмотрите на воду. Послушайте город вокруг вас.\n\nСегодня Грамаду будет говорить только с вами.",
    2: "🎧 Сцена 2 — Мечта о небе\n\nВот это здание. Колежиу Санто Дюмон.\n\nАльберту Сантус-Дюмон. Бразильцы убеждены — именно он первым поднял самолёт в воздух.",
    3: "🎧 Сцена 3 — Человек и шоколад\n\nВот этот переулочек. Маленькие магазинчики, никакой суеты.\n\nВ 1975 году молодой бразилец — Жайме Прауэр — приехал из Барилоче с рецептами и с одной идеей: шоколад должен быть историей.",
    4: "🍫 Остановка — Prawer Chocolates\n\nЗайдите. Посмотрите. Понюхайте — это важно.\n\nПопробуйте медленно — не торопитесь. Дайте второму вкусу появиться. Он всегда есть.\n\nКогда будете готовы — нажмите кнопку ниже.",
    5: "🎧 Сцена 4 — Красная дорожка в горах\n\nВот Палаціу дус Фестиваіс.\n\nСтарейший кинофестиваль Латинской Америки. С 1973 года.",
    6: "☕ Кофе в руках\n\nЗайдите, возьмите кофе с собой — и пойдём дальше.\n\nКофе в Бразилии — это не напиток. Это разговор.",
    7: "🎧 Сцена 6 — Город без светофоров\n\nСмотрите на этот перекрёсток. В Грамаду нет светофоров. Ни одного.\n\nВодители видят пешеходов. Пешеходы видят водителей. Все замечают друг друга.",
    8: "🍷 Остановка — Dunamis\n\nЗайдите. Сядьте.\n\nВ первом бокале — виноград.\nВо втором — характер земли.\nВ третьем — люди, которые это сделали.\n\nНе торопитесь.",
    9: "🎧 Сцена 8 — Город который не умеет молчать\n\nЗаметили огни?\n\nГрамаду — рождественская столица Бразилии. Здесь к Рождеству готовятся весь год.",
    10: "🎵 Просто идите.\n\nСлушайте город.\nНикаких слов — только музыка и улицы вокруг вас.",
    11: "🪨 Финал — Озеро\n\nВот мы и пришли.\n\nЭтот город начинался с первого камня. И каждый человек, который здесь оказывался, оставлял в нём что-то своё.\n\nСегодня вы прошли по этим улицам. Слышали их голоса. Чувствовали их вкус.\n\nСпасибо, что шли рядом.\n\nСнимите наушники.",
}


def read_token():
    if not os.path.exists(TOKEN_FILE):
        raise FileNotFoundError(f"Файл {TOKEN_FILE} не найден.")
    with open(TOKEN_FILE, "r", encoding="utf-8") as f:
        token = f.read().strip()
    if not token:
        raise ValueError(f"Файл {TOKEN_FILE} пустой.")
    return token


def read_codes():
    if not os.path.exists(CODES_FILE):
        return set()
    with open(CODES_FILE, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def read_used_codes():
    if not os.path.exists(USED_CODES_FILE):
        return set()
    with open(USED_CODES_FILE, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def mark_code_as_used(code):
    with open(USED_CODES_FILE, "a", encoding="utf-8") as f:
        f.write(code + "\n")


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return {}


def save_state(state):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_FILE)


def generate_promo():
    chars = string.ascii_uppercase + string.digits
    return "GRAMADO-" + "".join(random.choice(chars) for _ in range(5))


def is_active(user_data):
    if not user_data:
        return False
    expires = user_data.get("expires_at")
    if not expires:
        return False
    try:
        exp = datetime.fromisoformat(expires)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < exp
    except ValueError:
        return False


def start_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("НАЧАТЬ 🎧", callback_data="start_scenes")]])


def next_keyboard(scene):
    if scene in (4, 8):
        label = "МЫ НА МЕСТЕ →"
    else:
        label = "СЛЕДУЮЩАЯ СЦЕНА →"
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=f"scene_{scene + 1}")]])


def finish_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("СНЯТЬ НАУШНИКИ ✓", callback_data="finish")]])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = context.application.bot_data["state"]
    user_data = state.get(str(user_id))
    if is_active(user_data):
        await update.message.reply_text(
            "У вас уже есть активный доступ.\n\nНажмите кнопку ниже, чтобы продолжить.",
            reply_markup=start_keyboard()
        )
        return
    context.user_data["waiting_for_code"] = True
    await update.message.reply_text(
        "🎧 Добро пожаловать в «Голос города»!\n\n"
        "Это аудиоспектакль-прогулка по улицам Грамаду.\n\n"
        "Введите ваш код доступа:"
    )


async def check_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if not context.user_data.get("waiting_for_code"):
        return
    user_id = update.effective_user.id
    code = update.message.text.strip()
    codes = read_codes()
    used = read_used_codes()
    if code not in codes:
        await update.message.reply_text("❌ Неверный код. Проверьте и попробуйте ещё раз.")
        return
    if code in used:
        await update.message.reply_text("❌ Этот код уже был использован.")
        return
    mark_code_as_used(code)
    now = datetime.now(timezone.utc)
    expires = now + ACCESS_DURATION
    state = context.application.bot_data["state"]
    promo = generate_promo()
    state[str(user_id)] = {
        "code": code,
        "activated_at": now.isoformat(),
        "expires_at": expires.isoformat(),
        "scene": 0,
        "finished": False,
        "promo_code": promo,
        "promo_sent": False,
    }
    save_state(state)
    context.user_data["waiting_for_code"] = False
    await update.message.reply_text(
        "✅ Код принят!\n\nДоступ активирован на 24 часа.\n\nКогда будете готовы — нажмите кнопку ниже.",
        reply_markup=start_keyboard()
    )


async def send_scene(message, context, user_id, scene_number):
    state = context.application.bot_data["state"]
    user_data = state.get(str(user_id))
    if not is_active(user_data):
        await message.reply_text("⏰ Ваш доступ истёк.")
        return
    if scene_number < 1 or scene_number > 11:
        return
    audio_path = os.path.join(AUDIO_FOLDER, f"scena{scene_number}.mp3")
    if os.path.exists(audio_path):
        with open(audio_path, "rb") as audio:
            await message.reply_audio(audio=audio, title=f"Сцена {scene_number}")
    text = SCENE_TEXTS.get(scene_number, f"Сцена {scene_number}")
    if scene_number < 11:
        await message.reply_text(text, reply_markup=next_keyboard(scene_number))
    else:
        await message.reply_text(text, reply_markup=finish_keyboard())


async def start_scenes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    state = context.application.bot_data["state"]
    user_data = state.get(str(user_id))
    if not is_active(user_data):
        await query.message.reply_text("⏰ Ваш доступ истёк.")
        return
    user_data["scene"] = 1
    save_state(state)
    await send_scene(query.message, context, user_id, 1)


async def next_scene(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    state = context.application.bot_data["state"]
    user_data = state.get(str(user_id))
    if not is_active(user_data):
        await query.message.reply_text("⏰ Ваш доступ истёк.")
        return
    try:
        scene_number = int(query.data.replace("scene_", ""))
    except ValueError:
        return
    user_data["scene"] = scene_number
    save_state(state)
    await send_scene(query.message, context, user_id, scene_number)


async def finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    state = context.application.bot_data["state"]
    user_data = state.get(str(user_id))
    if not user_data:
        return
    user_data["finished"] = True
    save_state(state)
    promo = user_data.get("promo_code", generate_promo())
    await query.message.reply_text(
        f"Занавес! Спектакль завершён.\n\n"
        f"Ваш промокод на скидку 20% для следующего посещения или в подарок близким:\n\n"
        f"🎁 {promo}\n\n"
        f"Город всё ещё ждёт вас. 🪨"
    )


async def expiration_worker(application):
    while True:
        try:
            await asyncio.sleep(CHECK_INTERVAL)
            state = application.bot_data["state"]
            changed = False
            now = datetime.now(timezone.utc)
            for user_id, user_data in list(state.items()):
                if user_data.get("promo_sent"):
                    continue
                expires_str = user_data.get("expires_at")
                if not expires_str:
                    continue
                try:
                    expires = datetime.fromisoformat(expires_str)
                    if expires.tzinfo is None:
                        expires = expires.replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
                if now >= expires:
                    promo = user_data.get("promo_code", generate_promo())
                    try:
                        await application.bot.send_message(
                            chat_id=int(user_id),
                            text=(
                                f"⏰ Ваши 24 часа доступа завершились.\n\n"
                                f"Ваш промокод на скидку 20%:\n\n"
                                f"🎁 {promo}\n\n"
                                f"Подарите его близким или используйте для повторной покупки. 🪨"
                            )
                        )
                        user_data["promo_sent"] = True
                        changed = True
                    except Exception as e:
                        print(f"Ошибка отправки user_id={user_id}: {e}")
            if changed:
                save_state(state)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Ошибка expiration_worker: {e}")


async def post_init(application):
    application.bot_data["expiration_task"] = asyncio.create_task(
        expiration_worker(application)
    )


async def post_shutdown(application):
    task = application.bot_data.get("expiration_task")
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print(f"Ошибка: {context.error}")


def main():
    token = read_token()
    state = load_state()
    application = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    application.bot_data["state"] = state
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_code))
    application.add_handler(CallbackQueryHandler(start_scenes, pattern=r"^start_scenes$"))
    application.add_handler(CallbackQueryHandler(next_scene, pattern=r"^scene_(?:[1-9]|10|11)$"))
    application.add_handler(CallbackQueryHandler(finish, pattern=r"^finish$"))
    application.add_error_handler(error_handler)
    print("«Голос города» запущен!")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

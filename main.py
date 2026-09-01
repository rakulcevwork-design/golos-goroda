import os
import random
import string
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)


# ============================================================
# НАСТРОЙКИ
# ============================================================

# Файлы
CONFIG_FILE = "config.txt"
CODES_FILE = "codes.txt"
USED_CODES_FILE = "used_codes.txt"
USERS_FILE = "users.txt"

# Папка с аудиофайлами
AUDIO_FOLDER = "audio"

# Продолжительность доступа
ACCESS_HOURS = 24
ACCESS_TIME = timedelta(hours=ACCESS_HOURS)


# ============================================================
# ТЕКСТЫ СЦЕН
# ============================================================
#
# Здесь вставьте настоящие тексты сцен.
# Номер сцены должен соответствовать аудиофайлу:
#
# scena1.mp3  -> сцена 1
# scena2.mp3  -> сцена 2
# ...
# scena11.mp3 -> сцена 11
#

SCENES = {
    1: """
СЦЕНА 1

Здесь будет текст первой сцены.

Наденьте наушники и отправляйтесь
в путешествие по улицам Грамаду.
""",

    2: """
СЦЕНА 2

Здесь будет текст второй сцены.
""",

    3: """
СЦЕНА 3

Здесь будет текст третьей сцены.
""",

    4: """
СЦЕНА 4

Здесь будет текст четвёртой сцены.
""",

    5: """
СЦЕНА 5

Здесь будет текст пятой сцены.
""",

    6: """
СЦЕНА 6

Здесь будет текст шестой сцены.
""",

    7: """
СЦЕНА 7

Здесь будет текст седьмой сцены.
""",

    8: """
СЦЕНА 8

Здесь будет текст восьмой сцены.
""",

    9: """
СЦЕНА 9

Здесь будет текст девятой сцены.
""",

    10: """
СЦЕНА 10

Здесь будет текст десятой сцены.
""",

    11: """
СЦЕНА 11

Здесь будет текст финальной сцены.

Спасибо за это путешествие по Грамаду.
""",
}


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ФАЙЛОВ
# ============================================================

def read_config():
    """
    Читает токен Telegram-бота из config.txt.
    """

    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(
            f"Не найден файл {CONFIG_FILE}"
        )

    with open(CONFIG_FILE, "r", encoding="utf-8") as file:
        token = file.read().strip()

    if not token:
        raise ValueError(
            f"Файл {CONFIG_FILE} пустой"
        )

    return token


def read_valid_codes():
    """
    Читает доступные коды из codes.txt.

    Каждый код должен находиться на отдельной строке.
    """

    if not os.path.exists(CODES_FILE):
        return set()

    with open(CODES_FILE, "r", encoding="utf-8") as file:
        return {
            line.strip()
            for line in file
            if line.strip()
        }


def read_used_codes():
    """
    Читает использованные коды и промокоды.
    """

    if not os.path.exists(USED_CODES_FILE):
        return set()

    with open(USED_CODES_FILE, "r", encoding="utf-8") as file:
        return {
            line.strip()
            for line in file
            if line.strip()
        }


def save_used_access_code(code):
    """
    Записывает использованный код доступа.
    """

    with open(USED_CODES_FILE, "a", encoding="utf-8") as file:
        file.write(f"CODE:{code}\n")


def save_promo_code(promo):
    """
    Записывает выданный промокод.
    """

    with open(USED_CODES_FILE, "a", encoding="utf-8") as file:
        file.write(f"PROMO:{promo}\n")


# ============================================================
# ГЕНЕРАЦИЯ ПРОМОКОДА
# ============================================================

def generate_promo_code():
    """
    Генерирует уникальный промокод:

    GRAMADO-A7K9P
    """

    used_codes = read_used_codes()

    characters = string.ascii_uppercase + string.digits

    while True:
        random_part = "".join(
            random.choice(characters)
            for _ in range(5)
        )

        promo = f"GRAMADO-{random_part}"

        # Проверяем, не использовался ли такой промокод
        if f"PROMO:{promo}" not in used_codes:
            return promo


# ============================================================
# ХРАНЕНИЕ ПОЛЬЗОВАТЕЛЕЙ
# ============================================================
#
# Формат строки users.txt:
#
# user_id|activation_time|scene|active|message_ids
#
# Например:
#
# 123456789|2026-09-01T15:00:00|4|1|15,16,17,18
#

users = {}


def load_users():
    """
    Загружает пользователей из users.txt.
    """

    global users

    users = {}

    if not os.path.exists(USERS_FILE):
        return

    with open(USERS_FILE, "r", encoding="utf-8") as file:

        for line in file:
            line = line.strip()

            if not line:
                continue

            parts = line.split("|")

            if len(parts) != 5:
                continue

            try:
                user_id = int(parts[0])

                activation_time = datetime.fromisoformat(
                    parts[1]
                )

                scene = int(parts[2])

                active = parts[3] == "1"

                if parts[4]:
                    message_ids = [
                        int(x)
                        for x in parts[4].split(",")
                        if x
                    ]
                else:
                    message_ids = []

                users[user_id] = {
                    "activation_time": activation_time,
                    "scene": scene,
                    "active": active,
                    "message_ids": message_ids,
                }

            except (ValueError, IndexError):
                continue


def save_users():
    """
    Полностью сохраняет состояние пользователей
    в users.txt.
    """

    with open(USERS_FILE, "w", encoding="utf-8") as file:

        for user_id, data in users.items():

            activation_time = data["activation_time"].isoformat()

            scene = data["scene"]

            active = "1" if data["active"] else "0"

            message_ids = ",".join(
                str(message_id)
                for message_id in data["message_ids"]
            )

            file.write(
                f"{user_id}|"
                f"{activation_time}|"
                f"{scene}|"
                f"{active}|"
                f"{message_ids}\n"
            )


# ============================================================
# РАБОТА С MESSAGE ID
# ============================================================

def remember_message(user_id, message_id):
    """
    Запоминает ID сообщения.

    Благодаря этому через 24 часа бот сможет
    удалить сообщение.
    """

    if user_id not in users:
        return

    if message_id not in users[user_id]["message_ids"]:
        users[user_id]["message_ids"].append(message_id)

    save_users()


def forget_message(user_id, message_id):
    """
    Удаляет ID сообщения из списка сохранённых.
    """

    if user_id not in users:
        return

    if message_id in users[user_id]["message_ids"]:
        users[user_id]["message_ids"].remove(message_id)


# ============================================================
# ОТПРАВКА СООБЩЕНИЯ С СОХРАНЕНИЕМ ID
# ============================================================

async def send_message_and_remember(
    bot,
    user_id,
    text,
    **kwargs
):
    """
    Отправляет сообщение и запоминает его ID.
    """

    message = await bot.send_message(
        chat_id=user_id,
        text=text,
        **kwargs
    )

    remember_message(
        user_id,
        message.message_id
    )

    return message


async def send_audio_and_remember(
    bot,
    user_id,
    audio_path
):
    """
    Отправляет аудиофайл и запоминает ID сообщения.
    """

    with open(audio_path, "rb") as audio:

        message = await bot.send_audio(
            chat_id=user_id,
            audio=audio
        )

    remember_message(
        user_id,
        message.message_id
    )

    return message


# ============================================================
# УДАЛЕНИЕ ВСЕХ СОХРАНЁННЫХ СООБЩЕНИЙ
# ============================================================

async def delete_user_messages(bot, user_id):
    """
    Удаляет все сообщения, которые бот запомнил
    для конкретного пользователя.

    Это включает:
    - сообщения бота;
    - введённый пользователем код;
    - сообщения пользователя, которые мы получили
      во время работы бота.
    """

    if user_id not in users:
        return

    message_ids = list(
        users[user_id]["message_ids"]
    )

    for message_id in message_ids:

        try:

            await bot.delete_message(
                chat_id=user_id,
                message_id=message_id
            )

        except TelegramError:
            # Если сообщение уже удалено или Telegram
            # не разрешил его удалить — просто продолжаем.
            pass

    # После очистки списка больше ничего не храним
    users[user_id]["message_ids"] = []

    save_users()


# ============================================================
# ПРОВЕРКА АКТИВНОСТИ ДОСТУПА
# ============================================================

def is_access_active(user_id):
    """
    Проверяет, есть ли у пользователя активный доступ.
    """

    if user_id not in users:
        return False

    return users[user_id]["active"]


# ============================================================
# /START
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    # Запоминаем сообщение пользователя /start,
    # чтобы его тоже можно было удалить через 24 часа.
    if user_id in users:
        remember_message(
            user_id,
            update.message.message_id
        )

    # Если пользователь уже имеет активный доступ
    if is_access_active(user_id):

        keyboard = [
            [
                InlineKeyboardButton(
                    "НАЧАТЬ 🎧",
                    callback_data="start_show"
                )
            ]
        ]

        await send_message_and_remember(
            context.bot,
            user_id,
            "🎧 Доступ к «Голосу города» уже активирован.\n\n"
            "У вас есть 24 часа с момента активации.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        return

    # Если доступа нет
    await send_message_and_remember(
        context.bot,
        user_id,
        "🎧 Добро пожаловать в «Голос города»!\n\n"
        "Это аудиоспектакль-прогулка по улицам Грамаду.\n\n"
        "Введите ваш код доступа:"
    )


# ============================================================
# ПРОВЕРКА КОДА
# ============================================================

async def check_code(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    code = update.message.text.strip()

    # Если пользователь уже активен,
    # не воспринимаем обычный текст как новый код.
    if is_access_active(user_id):

        remember_message(
            user_id,
            update.message.message_id
        )

        await send_message_and_remember(
            context.bot,
            user_id,
            "🎧 Доступ уже активирован.\n\n"
            "Продолжайте спектакль с помощью кнопок."
        )

        return

    # Сохраняем введённый пользователем код
    #
    # Если пользователя ещё нет в users.txt,
    # временно создаём запись только для хранения сообщения.
    if user_id not in users:

        users[user_id] = {
            "activation_time": datetime.now(),
            "scene": 0,
            "active": False,
            "message_ids": [],
        }

    remember_message(
        user_id,
        update.message.message_id
    )

    # Загружаем коды
    valid_codes = read_valid_codes()
    used_codes = read_used_codes()

    # Код должен существовать в codes.txt
    if code not in valid_codes:

        await send_message_and_remember(
            context.bot,
            user_id,
            "❌ Такой код не найден.\n\n"
            "Проверьте правильность введённого кода."
        )

        return

    # Проверяем, не был ли код уже использован
    if f"CODE:{code}" in used_codes:

        await send_message_and_remember(
            context.bot,
            user_id,
            "❌ Этот код уже был использован."
        )

        return

    # --------------------------------------------------------
    # КОД ПРАВИЛЬНЫЙ
    # --------------------------------------------------------

    # Помечаем код как использованный
    save_used_access_code(code)

    # Время активации
    activation_time = datetime.now()

    # Создаём пользователя
    users[user_id] = {
        "activation_time": activation_time,
        "scene": 0,
        "active": True,

        # Сохраняем уже отправленное сообщение с кодом
        "message_ids": [
            update.message.message_id
        ],
    }

    save_users()

    # Запускаем таймер на 24 часа
    context.job_queue.run_once(
        access_expired,
        ACCESS_TIME,
        data=user_id,
        chat_id=user_id,
        name=f"access_{user_id}",
    )

    # Кнопка начала спектакля
    keyboard = [
        [
            InlineKeyboardButton(
                "НАЧАТЬ 🎧",
                callback_data="start_show"
            )
        ]
    ]

    await send_message_and_remember(
        context.bot,
        user_id,
        "✅ Код принят!\n\n"
        "Ваш доступ к «Голосу города» активирован "
        "на 24 часа.\n\n"
        "Найдите удобное место для начала прогулки, "
        "наденьте наушники и нажмите кнопку ниже.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ============================================================
# НАЧАЛО СПЕКТАКЛЯ
# ============================================================

async def start_show(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    # Проверяем доступ
    if not is_access_active(user_id):

        await send_message_and_remember(
            context.bot,
            user_id,
            "⏰ Ваш доступ к спектаклю уже завершён."
        )

        return

    # Начинаем с первой сцены
    users[user_id]["scene"] = 1

    save_users()

    # Отправляем сцену 1
    await send_scene(
        user_id,
        1,
        context
    )


# ============================================================
# ОТПРАВКА СЦЕНЫ
# ============================================================

async def send_scene(
    user_id,
    scene_number,
    context
):
    """
    Отправляет:
    1. аудио;
    2. текст;
    3. кнопку следующего действия.
    """

    audio_path = os.path.join(
        AUDIO_FOLDER,
        f"scena{scene_number}.mp3"
    )

    # Проверяем наличие аудио
    if not os.path.exists(audio_path):

        await send_message_and_remember(
            context.bot,
            user_id,
            f"⚠️ Не найден аудиофайл:\n"
            f"{audio_path}"
        )

        return

    # --------------------------------------------------------
    # ОТПРАВЛЯЕМ АУДИО
    # --------------------------------------------------------

    await send_audio_and_remember(
        context.bot,
        user_id,
        audio_path
    )

    # --------------------------------------------------------
    # ОПРЕДЕЛЯЕМ ТЕКСТ КНОПКИ
    # --------------------------------------------------------

    if scene_number == 11:

        button_text = "СНЯТЬ НАУШНИКИ ✓"

    elif scene_number in (4, 7):

        button_text = "МЫ НА МЕСТЕ →"

    else:

        button_text = "СЛЕДУЮЩАЯ СЦЕНА →"

    # --------------------------------------------------------
    # CALLBACK
    # --------------------------------------------------------

    callback_data = f"scene_{scene_number}"

    keyboard = [
        [
            InlineKeyboardButton(
                button_text,
                callback_data=callback_data
            )
        ]
    ]

    # --------------------------------------------------------
    # ОТПРАВЛЯЕМ ТЕКСТ СЦЕНЫ
    # --------------------------------------------------------

    await send_message_and_remember(
        context.bot,
        user_id,
        SCENES[scene_number],
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ============================================================
# СЛЕДУЮЩАЯ СЦЕНА
# ============================================================

async def next_scene(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    # Проверяем доступ
    if not is_access_active(user_id):

        await send_message_and_remember(
            context.bot,
            user_id,
            "⏰ Ваш доступ к спектаклю уже завершён."
        )

        return

    # Текущая сцена
    current_scene = users[user_id]["scene"]

    # Следующая сцена
    next_scene_number = current_scene + 1

    # За пределами спектакля ничего не делаем
    if next_scene_number > 11:
        return

    # Сохраняем номер сцены
    users[user_id]["scene"] = next_scene_number

    save_users()

    # Отправляем следующую сцену
    await send_scene(
        user_id,
        next_scene_number,
        context
    )


# ============================================================
# ФИНАЛЬНАЯ СЦЕНА
# ============================================================

async def finish_show(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    await query.answer()

    user_id = query.from_user.id

    # Проверяем доступ
    if not is_access_active(user_id):

        return

    # Генерируем промокод
    promo = generate_promo_code()

    # Сохраняем промокод
    save_promo_code(promo)

    # Закрываем доступ
    users[user_id]["active"] = False

    save_users()

    # Удаляем все сообщения спектакля
    await delete_user_messages(
        context.bot,
        user_id
    )

    # Финальное сообщение НЕ добавляем в список
    # сообщений для удаления.
    #
    # Поэтому оно останется в чате.
    await context.bot.send_message(
        chat_id=user_id,
        text=(
            'Занавес! Ваш доступ к спектаклю '
            '"Голос города" закрыт.\n\n'
            'Ваш промо-код для покупки нового доступа '
            'со скидкой 30%:\n\n'
            f'{promo}\n\n'
            'Подарите его тем, кому тоже стоит услышать '
            'Голос города или используйте его для '
            'повторной покупки.'
        )
    )


# ============================================================
# ОКОНЧАНИЕ ДОСТУПА ЧЕРЕЗ 24 ЧАСА
# ============================================================

async def access_expired(
    context: ContextTypes.DEFAULT_TYPE
):

    # Получаем ID пользователя из Job.data
    user_id = context.job.data

    # Пользователь мог завершить спектакль раньше.
    # В этом случае ничего не делаем.
    if user_id not in users:
        return

    if not users[user_id]["active"]:
        return

    # --------------------------------------------------------
    # ЗАКРЫВАЕМ ДОСТУП
    # --------------------------------------------------------

    users[user_id]["active"] = False

    save_users()

    # --------------------------------------------------------
    # УДАЛЯЕМ СООБЩЕНИЯ
    # --------------------------------------------------------

    await delete_user_messages(
        context.bot,
        user_id
    )

    # --------------------------------------------------------
    # ГЕНЕРИРУЕМ ПРОМОКОД
    # --------------------------------------------------------

    promo = generate_promo_code()

    save_promo_code(promo)

    # --------------------------------------------------------
    # ОТПРАВЛЯЕМ ФИНАЛЬНОЕ СООБЩЕНИЕ
    # --------------------------------------------------------
    #
    # Это сообщение специально НЕ сохраняем в users.txt.
    # Оно должно остаться у пользователя.
    #

    await context.bot.send_message(
        chat_id=user_id,
        text=(
            'Занавес! Ваш доступ к спектаклю '
            '"Голос города" закрыт.\n\n'
            'Ваш промо-код для покупки нового доступа '
            'со скидкой 30%:\n\n'
            f'{promo}\n\n'
            'Подарите его тем, кому тоже стоит услышать '
            'Голос города или используйте его для '
            'повторной покупки.'
        )
    )


# ============================================================
# ВОССТАНОВЛЕНИЕ ТАЙМЕРОВ ПОСЛЕ ПЕРЕЗАПУСКА
# ============================================================

def restore_timers(application):
    """
    После запуска бота проверяем пользователей,
    которые были активны до перезапуска.

    Если 24 часа ещё не прошли —
    создаём новый таймер на оставшееся время.

    Если 24 часа уже прошли —
    запускаем завершение доступа практически сразу.
    """

    now = datetime.now()

    for user_id, data in users.items():

        if not data["active"]:
            continue

        expiration_time = (
            data["activation_time"]
            + ACCESS_TIME
        )

        remaining_time = (
            expiration_time - now
        )

        if remaining_time.total_seconds() <= 0:

            # 24 часа уже прошли.
            #
            # Ставим задачу на 1 секунду,
            # чтобы она выполнилась после запуска.
            application.job_queue.run_once(
                access_expired,
                1,
                data=user_id,
                chat_id=user_id,
                name=f"access_{user_id}",
            )

        else:

            # 24 часа ещё не прошли.
            application.job_queue.run_once(
                access_expired,
                remaining_time,
                data=user_id,
                chat_id=user_id,
                name=f"access_{user_id}",
            )


# ============================================================
# ОБРАБОТКА ОШИБОК
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):
    """
    Выводит ошибки в консоль.
    """

    print(
        "Произошла ошибка:",
        context.error
    )


# ============================================================
# ЗАПУСК БОТА
# ============================================================

def main():

    print("Запуск «Голос города»...")

    # --------------------------------------------------------
    # ЧИТАЕМ ТОКЕН
    # --------------------------------------------------------

    token = read_config()

    # --------------------------------------------------------
    # ЗАГРУЖАЕМ СОХРАНЁННЫХ ПОЛЬЗОВАТЕЛЕЙ
    # --------------------------------------------------------

    load_users()

    print(
        f"Загружено пользователей: {len(users)}"
    )

    # --------------------------------------------------------
    # СОЗДАЁМ APPLICATION
    # --------------------------------------------------------

    application = (
        Application.builder()
        .token(token)
        .build()
    )

    # --------------------------------------------------------
    # КОМАНДА /START
    # --------------------------------------------------------

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # --------------------------------------------------------
    # КНОПКА «НАЧАТЬ»
    # --------------------------------------------------------

    application.add_handler(
        CallbackQueryHandler(
            start_show,
            pattern=r"^start_show$"
        )
    )

    # --------------------------------------------------------
    # ФИНАЛЬНАЯ КНОПКА СЦЕНЫ 11
    # --------------------------------------------------------

    application.add_handler(
        CallbackQueryHandler(
            finish_show,
            pattern=r"^scene_11$"
        )
    )

    # --------------------------------------------------------
    # КНОПКИ СЦЕН 1–10
    # --------------------------------------------------------

    application.add_handler(
        CallbackQueryHandler(
            next_scene,
            pattern=r"^scene_(?:[1-9]|10)$"
        )
    )

    # --------------------------------------------------------
    # ЛЮБОЙ ТЕКСТ
    #
    # Если пользователь не использует команду,
    # текст воспринимается как код доступа.
    # --------------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            check_code
        )
    )

    # --------------------------------------------------------
    # ОБРАБОТЧИК ОШИБОК
    # --------------------------------------------------------

    application.add_error_handler(
        error_handler
    )

    # --------------------------------------------------------
    # ВОССТАНАВЛИВАЕМ ТАЙМЕРЫ
    # --------------------------------------------------------

    restore_timers(application)

    # --------------------------------------------------------
    # ЗАПУСК
    # --------------------------------------------------------

    print("«Голос города» запущен!")

    application.run_polling()


# ============================================================
# ЗАПУСК ПРОГРАММЫ
# ============================================================

if __name__ == "__main__":
    main()
```


import os
import webbrowser
import subprocess
import pyperclip  # Для работы с буфером обмена
import psutil  # Для управления процессами
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import ImageGrab  # Для создания скриншотов
import fnmatch  # Для поиска файлов по шаблону

# Конфигурация
TOKEN = "Токен вашего бота"  # Замените на ваш реальный токен
ALLOWED_USER_IDS = {123456789}  # Список разрешённых ID
DOWNLOAD_FOLDER = r"C:\Загрузки с телефона"  # Папка для сохранения файлов
SCREENSHOT_PATH = os.path.join(DOWNLOAD_FOLDER, "screenshot.png")  # Путь для сохранения скриншота

SEARCH_DIRECTORIES = [
    r"C:\Program Files",
    r"C:\Program Files (x86)",
    r"C:\Users\maksl\Desktop",
    r"C:\Windows",
    r"C:\Users\maksl\Documents",
    r"C:\Users\maksl\AppData\Roaming",
    r"C:\Users\maksl\AppData\Local"
]

# Создаём папку для загрузок, если её нет
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)


def find_file(file_name):
    """
    Ищет файл по всему диску C: в указанных директориях.
    Возвращает полный путь к файлу, если он найден, иначе None.
    """
    for directory in SEARCH_DIRECTORIES:
        for root, dirs, files in os.walk(directory):
            for name in fnmatch.filter(files, file_name):
                return os.path.join(root, name)
    return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USER_IDS:
        return

    # Создаём клавиатуру с одной кнопкой "Выключить"
    keyboard = [["Выключить", "Сделать скриншот"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "Выберите действие:",
        reply_markup=reply_markup
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USER_IDS:
        return

    text = update.message.text

    # Обработка команды "Выключить"
    if text == "Выключить":
        # Устанавливаем флаг, что бот ожидает ввода времени
        context.user_data["waiting_for_shutdown_time"] = True
        await update.message.reply_text("Введите количество минут, через которое выключить компьютер:")
        return

    # Обработка времени выключения
    if context.user_data.get("waiting_for_shutdown_time"):
        try:
            minutes = int(text)
            seconds = minutes * 60
            subprocess.run(f"shutdown /s /t {seconds}", shell=True)
            await update.message.reply_text(f"Компьютер выключится через {minutes} минут.")
            context.user_data["waiting_for_shutdown_time"] = False  # Сбрасываем флаг
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите число (минуты).")
        return

    # Обработка программ (если текст заканчивается на .exe)
    elif text.lower().endswith(".exe"):
        try:
            # Ищем файл по всему диску
            file_path = find_file(text)
            if file_path:
                os.startfile(file_path)
                await update.message.reply_text(f"Запускаю программу: {file_path}")
            else:
                await update.message.reply_text(f"Программа {text} не найдена.")
        except Exception as e:
            await update.message.reply_text(f"Ошибка: {str(e)}")

    # Обработка ссылок (если текст содержит точку, но не заканчивается на .exe)
    elif "." in text and not text.lower().endswith(".exe"):
        if not text.startswith(("http://", "https://")):
            text = f"https://{text}"  # Добавляем https://, если его нет
        webbrowser.open(text)

    # Создание скриншота
    elif text == "Сделать скриншот":
        try:
            # Создаём скриншот
            screenshot = ImageGrab.grab()
            screenshot.save(SCREENSHOT_PATH)

            # Отправляем скриншот
            with open(SCREENSHOT_PATH, "rb") as photo:
                await update.message.reply_photo(photo)

            # Удаляем скриншот после отправки
            os.remove(SCREENSHOT_PATH)
        except Exception as e:
            await update.message.reply_text(f"Ошибка при создании скриншота: {str(e)}")

    # Если команда не распознана
    else:
        await update.message.reply_text(
            "Не понимаю команду. Введите ссылку (например, youtube.com), имя программы (например, notepad.exe) или выберите действие из меню.")


async def cancel_shutdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USER_IDS:
        return
    subprocess.run("shutdown /a", shell=True)
    await update.message.reply_text("Выключение отменено!")


async def copy_to_clipboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USER_IDS:
        return

    # Получаем текст после команды /copy
    text_to_copy = update.message.text.replace("/copy", "").strip()

    if not text_to_copy:
        await update.message.reply_text("Пожалуйста, укажите текст для копирования. Пример: /copy Привет, мир!")
        return

    try:
        # Копируем текст в буфер обмена
        pyperclip.copy(text_to_copy)
        await update.message.reply_text(f"Текст скопирован в буфер обмена: {text_to_copy}")
    except Exception as e:
        await update.message.reply_text(f"Ошибка при копировании текста: {str(e)}")


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USER_IDS:
        return

    # Получаем файл из сообщения
    file = await update.message.document.get_file()
    file_name = update.message.document.file_name

    # Сохраняем файл в папку
    file_path = os.path.join(DOWNLOAD_FOLDER, file_name)
    await file.download_to_drive(file_path)

    await update.message.reply_text(f"Файл сохранён: {file_path}")


async def close_application(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_USER_IDS:
        return

    # Получаем имя программы из команды /close
    app_name = context.args[0] if context.args else None

    if not app_name:
        await update.message.reply_text("Пожалуйста, укажите имя программы. Пример: /close notepad.exe")
        return

    try:
        # Ищем и завершаем процесс
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'].lower() == app_name.lower():
                proc.terminate()
                await update.message.reply_text(f"Программа {app_name} успешно закрыта.")
                return
        await update.message.reply_text(f"Программа {app_name} не найдена.")
    except Exception as e:
        await update.message.reply_text(f"Ошибка при закрытии программы: {str(e)}")


def main():
    app = Application.builder().token(TOKEN).build()

    # Регистрируем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel_shutdown))
    app.add_handler(CommandHandler("copy", copy_to_clipboard))  # Обработчик команды /copy
    app.add_handler(CommandHandler("close", close_application))  # Обработчик команды /close
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))  # Обработчик файлов

    app.run_polling()

    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(send_startup_message(app))


if __name__ == "__main__":
    main()

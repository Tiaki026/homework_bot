import os
import sys
import json
import time
import logging
import re
import requests
from http import HTTPStatus
from datetime import datetime
from dotenv import load_dotenv
import telegram
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from apscheduler.schedulers.background import BackgroundScheduler
import exceptions


load_dotenv()
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_PERIOD = 600
UTC_OFFSET = 3 * 60 * 60
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!😊❤️🚀',
    'reviewing': 'Работа взята на проверку ревьюером. 🗒',
    'rejected': 'Работа проверена: у ревьюера есть замечания. 😱🙈🤯'
}


def check_tokens() -> str:
    """Проверка токенов."""
    return PRACTICUM_TOKEN and TELEGRAM_CHAT_ID and TELEGRAM_TOKEN


def send_message(bot, message, chat_id) -> None:
    """Отправка сообщений."""
    logging.info('Начало отправки сообщения')
    try:
        bot.send_message(chat_id=chat_id, text=message)
        logging.debug('Сообщение успешно отправлено')
    except telegram.error.TelegramError as error:
        logging.exception(
            f'Ошибка отправки сообщения: {error}'
        )


def get_api_answer(timestamp) -> any:
    """Запрос к API."""
    logging.info('Начало запроса к API')
    try:
        response = requests.get(
            url=ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
    except requests.RequestException as error:
        raise ConnectionError(
            f'Ошибка подключения: {error}'
        )
    if response.status_code != HTTPStatus.OK:
        raise exceptions.ApiResponseFailed(
            f'API не отвечает. Статус: {response.status_code}'
        )
    try:
        response_json = response.json()
    except json.JSONDecodeError as error:
        logging.exception(f'Не удалось расшифровать JSON-овтет: {error}')
        raise ValueError(f'Не удалось расшифровать JSON-овтет: {error}')
    return response_json


def check_response(response) -> list:
    """Проверка ответа."""
    if not isinstance(response, dict):
        raise TypeError(
            f'Данные - {type(response)} не соответствуют типу "dict".'
        )
    if 'homeworks' not in response:
        raise KeyError('Работы не существует')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError(
            f'Данные - {type(homeworks)} не соответствуют типу "list".'
        )
    return homeworks


def parse_status(homeworks) -> str:
    """Парсинг статусов всех работ."""
    messages = []
    for homework in homeworks:
        if 'homework_name' not in homework:
            raise KeyError(
                f'{"homework_name"} не найдено.'
            )
        if 'status' not in homework:
            raise KeyError(
                'Статус - {"status"} не определён.'
            )
        status = homework.get('status')
        if status not in HOMEWORK_VERDICTS:
            raise ValueError(
                f'Неизвестный стататус - {status}.'
            )
        homework_name = homework.get('homework_name')
        reviewer_comment = homework.get('reviewer_comment')
        date_updated = homework.get('date_updated')
        parsed_date = datetime.strptime(date_updated, "%Y-%m-%dT%H:%M:%SZ")
        formatted_date = parsed_date.strftime(
            "Работа проверена %d.%m.%Y в %H:%M"
        )
        lesson_name = homework.get('lesson_name')
        id_work = homework.get('id')
        verdict = HOMEWORK_VERDICTS[status]
        messages.append(
            f'‼️ Изменился статус проверки работы ‼️ \n'
            f'🛠 {lesson_name}.\n' 
            f'🖥 "{homework_name}".\n'
            f'🗣 "{verdict}".\n'
            f'📓 "{reviewer_comment}"\n'
            f'⏳ {formatted_date}.\n'
            f' \n'
            f'ID {id_work}. '
            )
    if messages:
        return '\n\n'.join(messages)


def status_by_date(update: Update, context: CallbackContext) -> None:
    """Статус по дате из сообщения."""
    user_id = update.message.from_user.id
    message_text = update.message.text

    date_pattern = re.compile(r'(\d{2}\.\d{2}\.\d{4})')
    match = date_pattern.search(message_text)

    if match:
        date_str = match.group(1)
        desired_unix_timestamp = date_to_unix_timestamp(date_str)

        if desired_unix_timestamp is not None:
            desired_unix_timestamp -= UTC_OFFSET

            try:
                response = get_api_answer(desired_unix_timestamp)
                print("API Response:", response)
                homeworks = check_response(response)
            except Exception as e:
                print("Error during API request:", str(e))
                send_message(
                    context.bot,
                    "Ошибка при запросе к API",
                    chat_id=user_id
                )
                return

            if homeworks:
                message = parse_status(homeworks)
                send_message(context.bot, message, chat_id=user_id)
            else:
                send_message(
                    context.bot,
                    "Для указанной даты нет статусов. 😵",
                    chat_id=user_id
                )
        else:
            send_message(
                context.bot,
                "Неправильный формат даты. 🙈 Используйте ДД.ММ.ГГГГ",
                chat_id=user_id
            )
    else:
        send_message(
            context.bot,
            "Укажите дату в формате ДД.ММ.ГГГГ. Например /status 01.01.2023",
            chat_id=user_id
        )


def date_to_unix_timestamp(date_str):
    """Первод даты в Unix-формат."""
    try:
        date_obj = datetime.strptime(date_str, "%d.%m.%Y")
        unix_timestamp = int(date_obj.timestamp()) - UTC_OFFSET
        return unix_timestamp
    except ValueError:
        return None


def check_homework_statuses(bot):
    timestamp = int(time.time())
    last_message = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                if last_message != message:
                    send_message(bot, message)
                    last_message = message
            timestamp = response.get('current_date', timestamp)
        except Exception as error:
            message = f'Ошибка работы программы: {error}'
            logging.exception(message)
            if last_message != message:
                send_message(bot, message)
                last_message = message
        finally:
            time.sleep(RETRY_PERIOD)


def main():
    """Основная логика работы бота."""
    logging.info("Бот запущен и готов к работе.")
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("status", status_by_date))

    if not check_tokens():
        logging.critical('Ошибка токена')
        sys.exit()
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        check_homework_statuses,
        'interval',
        seconds=RETRY_PERIOD,
        args=[updater.bot]
    )
    scheduler.start()
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    logging.getLogger('apscheduler').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(
                filename='homework.log', mode='w', encoding='UTF-8'),
            logging.StreamHandler(stream=sys.stdout)
        ],
        format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
    )
    main()

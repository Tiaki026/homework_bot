import os
import sys
import json
import time
import logging
import requests
import telegram
import exceptions
from http import HTTPStatus
from dotenv import load_dotenv


load_dotenv()
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка токенов."""
    return PRACTICUM_TOKEN and TELEGRAM_CHAT_ID and TELEGRAM_TOKEN


def send_message(bot, message):
    """Отправка сообщений."""
    logging.info('Начало отправки сообщения')
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug('Сообщение успешно отправлено')
    except telegram.error.TelegramError as error:
        logging.exception(
            f'Ошибка отправки сообщения: {error}'
        )


def get_api_answer(timestamp):
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


def check_response(response):
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


def parse_status(homework):
    """Проверка статуса работы."""
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
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_message = ''
    if not check_tokens():
        logging.critical('Ошибка токена')
        sys.exit()
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


if __name__ == '__main__':
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

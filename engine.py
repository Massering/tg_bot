from telebot.types import *
from random import choice
from datetime import datetime as dt, timedelta as td
import pymorphy2

from config import *

morph = pymorphy2.MorphAnalyzer()


def get_date() -> str:
    """Получение строки с датой и временем сейчас"""
    return dt.now().strftime("%y.%m.%d %H:%M:%S")


def get_planning_day(need_date=True) -> str:
    """Получение строки с датой и временем, на которые будут записаны данные"""

    months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля',
              'августа', 'сентября', 'октября', 'ноября', 'декабря']
    weekdays = ['понедельник', 'вторник', 'среду', 'четверг', 'пятницу', 'субботу', 'воскресенье']

    now = dt.now()
    delta = now > now.replace(**dict(zip(['hour', 'minute'], map(int, MORNING_TIME.split(':')))))
    delta += now.weekday() == 6 - delta

    date = now + td(days=delta)
    return f'{weekdays[date.weekday()]}' + f' ({date.day} {months[date.month - 1]})' * need_date


def dump(obj: Union[list, dict, str], filename: str) -> None:
    """Функция для простого внесения данных в файлы"""
    json.dump(obj, open(filename, 'w', encoding=ENCODING), ensure_ascii=False, indent=4)


def make_bool_keyboard(one_time=True) -> ReplyKeyboardMarkup:
    """Возвращает клавиатуру, состоящую из кнопок 'Да' и 'Нет'"""
    keyboard = ReplyKeyboardMarkup(True, one_time_keyboard=one_time)
    keyboard.add(KeyboardButton('Да'), KeyboardButton('Нет'))
    return keyboard


def make_keyboard(values: iter, one_time=True) -> ReplyKeyboardMarkup:
    """Возвращает клавиатуру, содержащую кнопки со значениями values"""
    keyboard = ReplyKeyboardMarkup(True, one_time_keyboard=one_time)
    for value in values:
        key1 = KeyboardButton(value)
        keyboard.add(key1)
    return keyboard


def get_fullname(message: Message) -> str:
    """Возвращает ФИ пользователя, под которыми он зарегистрирован в Телеграмм"""
    name = (message.from_user.last_name or ' ') + ' ' + message.from_user.first_name
    return name.strip().title()


def reform(word: str, main_word: Union[int, str]) -> str:
    word_form: pymorphy2.analyzer.Parse = morph.parse(word)[0]
    if isinstance(main_word, int):
        return word_form.make_agree_with_number(main_word).word
    return word_form.word


def make_empty_message(chat_id: Union[str, int]) -> Message:
    chat = Chat(int(chat_id), None)
    return Message(0, chat, '', chat, '', '', '')

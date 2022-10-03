from telebot.types import *
from datetime import datetime as dt, timedelta as td, date
import pymorphy2

from config import *

# Чтобы изменять слова по числительным
morph = pymorphy2.MorphAnalyzer()


def get_now() -> dt:
    """Получение даты и времени сейчас. Используется везде вместо dt.now() чтобы имитировать другой день"""
    return dt.now()


def get_date() -> str:
    """Получение строки с датой и временем сейчас"""
    return get_now().strftime("%d.%m.%y %H:%M:%S")


def get_planning_day(formatted=True, need_date=True, na=False, need_weekday=True, strong=0) -> Union[str, date]:
    """Получение строки с датой и временем, на которые будут записаны данные"""
    # Возможно, стоит разделить эту функцию на много разных, каждая из которых будет отвечать за свой параметр
    # И вызывать эту, но только для получения даты в формате datetime

    months = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
              'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
    weekdays = ['понедельник', 'вторник', 'среду', 'четверг', 'пятницу', 'субботу', 'воскресенье']
    v_weekdays = [['в ', 'во '][day == 'вторник'] + day for day in weekdays]
    na_weekdays = ['на ' + day for day in weekdays]

    # Дата сейчас
    now = get_now()
    report_time = now.replace(**dict(zip(['hour', 'minute'], map(int, REPORT_TIME.split(':')))))
    friday_report_time = now.replace(**dict(zip(['hour', 'minute'], map(int, FRIDAY_REPORT_TIME.split(':')))))

    #         ПН    ВТ    СР    ЧТ    ПТ    СБ   ВС
    delta = [1, 2, 1, 2, 1, 2, 1, 2, 1, 4, 3, 3, 2, 2][now.weekday() * 2 + (now > report_time + td(minutes=strong * 5))]
    if now.weekday() == 4 and report_time + td(minutes=strong * 5) < now < friday_report_time:
        delta -= 1

    planning_date = now + td(days=delta)

    if not formatted:  # Бывает, что нужна именно дата в типе date
        return planning_date.date()

    weekday = [v_weekdays, na_weekdays][na][planning_date.weekday()]

    return f'{weekday}' * need_weekday + f' ({planning_date.day} {months[planning_date.month - 1]})' * need_date


def dump(obj: Union[list, dict, str], filename: str) -> None:
    """Функция для упрощения внесения данных в файлы"""
    if isinstance(obj, str):
        open(filename, 'w', encoding=ENCODING).write(obj)
    else:  # Для записи с использованием моей функции format_json
        json.dump(obj, open(filename, 'w', encoding=ENCODING), ensure_ascii=False, indent=2)


def bool_keyboard(one_time=True) -> ReplyKeyboardMarkup:
    """Возвращает клавиатуру, состоящую из кнопок 'Да' и 'Нет'"""
    my_keyboard = ReplyKeyboardMarkup(True, one_time_keyboard=one_time)
    my_keyboard.add(KeyboardButton(YES.capitalize()), KeyboardButton(NO.capitalize()))
    return my_keyboard


def choice_keyboard(one_time=True) -> ReplyKeyboardMarkup:
    """Возвращает клавиатуру, состоящую из кнопок 'Да' и 'Нет'"""
    my_keyboard = ReplyKeyboardMarkup(True, one_time_keyboard=one_time)
    my_keyboard.add(KeyboardButton(YES.capitalize()), KeyboardButton(NO.capitalize()))
    my_keyboard.add(KeyboardButton(ALWAYS.capitalize()), KeyboardButton(ALWAYS_NOT.capitalize()))
    return my_keyboard


def change_keyboard(student: dict) -> ReplyKeyboardMarkup:
    return keyboard([f'Завтрак ({[NO, YES, ALWAYS, ALWAYS_NOT][student[BREAKFAST]]})',
                     f'Обед ({[NO, YES, ALWAYS, ALWAYS_NOT][student[LUNCH]]})',
                     f'Полдник ({[NO, YES, ALWAYS, ALWAYS_NOT][student[POLDNIK]]})',
                     f'Все'])


def keyboard(values: iter, one_time=True) -> ReplyKeyboardMarkup:
    """Возвращает клавиатуру, содержащую кнопки со значениями values"""
    my_keyboard = ReplyKeyboardMarkup(True, one_time_keyboard=one_time)
    for value in values:
        key1 = KeyboardButton(value)
        my_keyboard.add(key1)
    return my_keyboard


def reform(word: str, n: int) -> str:
    """Возвращает слово, измененное под числительное, переданное вторым параметром"""
    if word == 'будет':
        if n == 1:
            return word
        return 'будут'

    word_form: pymorphy2.analyzer.Parse = morph.parse(word)[0]
    return word_form.make_agree_with_number(n).word


def create_message(chat_id: int) -> Message:
    """Создание (имитация) пустого сообщения от пользователя"""
    # Кажется, этого не было задумано в этой библиотеке

    chat = Chat(int(chat_id), 'private')
    return Message(0, chat, dt.now(), chat, 'text', '', '')


def format_json(m, level=0, indent=4) -> str:
    """Получает список или словарь, возвращает строку, отформатированную почти по формату JSON.
    Писал сам, в целях экономии символов в файле STAT"""
    margin = ' ' * indent * level
    if isinstance(m, dict):
        text = '{' + '\n' * bool(m)
        for n, i in enumerate(m, 1):
            text += margin + ' ' * indent + f'"{str(i)}": '
            text += format_json(m[i], level + 1, indent=indent)
            if n != len(m):
                text += ',\n'
            else:
                text += '\n'
        text += '}'
    else:
        if m and isinstance(m[0], list):
            text = '[\n'
            for n, i in enumerate(m, 1):
                text += margin + ' ' * indent
                text += format_json(i, level + 1, indent=indent)
                if n != len(m):
                    text += ',\n'
                else:
                    text += '\n'
            text += margin + ']'

        else:
            text = str(list(m)).replace("'", '"')
    return text

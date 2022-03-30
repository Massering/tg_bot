import os

import requests
import schedule
from threading import Thread

from time import sleep

import telebot

from engine import *
from config import *

if not os.path.exists(USERS):
    dump({DELETED: {}}, USERS)
    # raise FileNotFoundError(f'ФАЙЛ {USERS} НЕ СУЩЕСТВУЕТ')
users = json.load(open(USERS, 'r', encoding=ENCODING))
users = {i if i == DELETED else int(i): users[i] for i in users}
users[DELETED] = {int(i): users[DELETED][i] for i in users[DELETED]}

bot = telebot.TeleBot(TOKEN)


def send_message(user_id: Union[int, str], text: str, *args, reply_markup=None, **kwargs):
    log((text.strip(), user_id))
    if isinstance(user_id, str):
        user_id = eval(user_id)
    bot.send_message(user_id, text, *args, reply_markup=reply_markup, **kwargs)


def send_message_by_input():
    last_id, user_id, text = [None] * 3
    while 1:
        try:
            user_id, *text = input().split()
            send_message(user_id, ' '.join(text))
            last_id = user_id
        except (telebot.apihelper.ApiException, NameError):   # Пользователя не существует
            if last_id:
                try:
                    send_message(last_id, ' '.join([user_id] + text))
                except Exception as error:
                    log(f'Лох, как ты смог допустить ошибку "{error}"')
        except Exception as error:
            log(f'Лох, как ты смог допустить ошибку "{error.__class__} - {error}"')


def log(message, starting=False):
    """Вывод в консоль уведомления о сообщении боту + Проверка сообщения (выход)"""

    if isinstance(message, Message):
        name = get_fullname(message)
        name += f' (id {message.from_user.id})'
        print(f'{get_date()} - {name}: "{message.text}"')

        if message.text == '/exit':
            send_message(message.from_user.id, f'Выход из сценария')
            return 1

        if message.text[0] == '/' and not starting:
            start(message)
            return 1

    elif isinstance(message, tuple):
        print(f'{get_date()} - this Bot to {message[1]}: "{message[0]}"')

    else:
        print(f'{get_date()} - system_log: "{message}"')


@bot.message_handler(content_types=['text'])
def start(message: Message):
    """Изначальная функция, принимающая запросы пользователя"""
    if log(message, starting=True):
        return

    if message.text == '/start':
        send_message(message.from_user.id, f'''
Это бот ФМШ СФУ, созданный, чтобы опрашивать учеников, будут ли они обедать

Данные записываются на ближайший учебный день. Данные можно изменить только до {REPORT_TIME} того же дня.
В {REPORT_TIME} бот отправляет классному советнику всю информацию.
После этого времени бот будет спрашивать данные на следующий учебный день.

Также бот отправит вам напоминание в {EVENING_TIME} и в {MORNING_TIME}, если вы до сих пор не внесли данные

Если вы классный советник, напишите "Я классный советник" и больше ничего не пишите, вам не нужно регистрироваться

Создатель: Рудаков Максим из Йоты
@chmorodinka
''')

    if message.text == '/send_message':
        send_message(message.from_user.id, 'Первое слово следующего сообщения будет использовано как id, а '
                                           'остальные отправлены как текст.')
        bot.register_next_step_handler(message, send_message_by_id)

    elif message.from_user.id in CLASSES.values():
        *_, cur_class = sorted(i[0] for i in CLASSES.items() if i[1] == message.from_user.id)

        if message.text == '/my_class':
            text = 'Список учеников вашего класса:\n'
            for n, student in enumerate(x for x in users if x != DELETED and users[x][CLASS] == cur_class):
                text += f'{n + 1}. {users[student][NAME]} (id{student})'
            send_message(message.from_user.id, text)

        elif message.text == '/report':
            send_report(clear=False, classes=[cur_class])

        else:
            send_message(message.from_user.id, TEACHER_COMMANDS)

    elif message.from_user.id not in users:
        send_message(message.from_user.id, 'Хочешь зарегистрироваться?',
                     reply_markup=make_bool_keyboard())
        bot.register_next_step_handler(message, if_register)

    elif message.text.lower() in ['/menu', 'меню', '/commands', 'команды']:
        send_message(message.from_user.id, bot.get_my_commands() or 'Nothing')

    elif message.text == '/change_name':
        send_message(message.from_user.id, 'Введи новое имя. Имей в виду, что твой классный советник '
                                           'будет уведомлен об изменении имени (/exit если вдруг передумал)',
                     reply_markup=make_keyboard({get_fullname(message), users[message.from_user.id][NAME]}))
        bot.register_next_step_handler(message, change_name)

    elif message.text == '/del_myself':
        send_message(message.from_user.id, 'Ты уверен, что хочешь удалить свои данные из системы?',
                     reply_markup=make_bool_keyboard())
        bot.register_next_step_handler(message, del_user)

    else:
        send_message(message.from_user.id, f'Хочешь изменить данные на {get_planning_day(need_date=False)}?',
                     reply_markup=make_bool_keyboard())
        bot.register_next_step_handler(message, get_if_want_to_change_data)


def send_message_by_id(message: Message):
    try:
        user_id, *text = message.text.split()

        if message.from_user.id == MAKSIM:
            send_message(user_id, ' '.join(text))
        else:
            send_message(user_id, f'id{message.from_user.id}: \n{" ".join(text)}')

        send_message(message.from_user.id, f'Отправлено to id{user_id} "{" ".join(text)}"')

    except Exception as error:
        send_message(message.from_user.id, f'Лох, как ты смог допустить ошибку "{error.__class__} - {error}"')


def del_user(message: Message):
    """Функция, получающая, хочет ли пользователь удалить свои данные"""
    if log(message):
        return

    if message.text.lower() == 'да':
        users[DELETED][message.from_user.id] = users[message.from_user.id]
        del users[message.from_user.id]
        dump(users, USERS)

        send_message(message.from_user.id, 'Очень жаль, что ты покидаешь нас. Прощай')

    else:
        send_message(message.from_user.id, 'Ну и славно)')


def change_name(message: Message):
    """Функция, получающая, хочет ли пользователь удалить свои данные"""
    if log(message):
        return

    user = users[message.from_user.id]
    send_message(message.from_user.id, f'Имя {user[NAME]} изменено на {message.text}')
    send_message(CLASSES[user[CLASS]], f'Имя ученика {user[NAME]} изменено на {message.text}')

    users[message.from_user.id][NAME] = message.text
    dump(users, USERS)


def get_if_want_to_change_data(message: Message):
    """Функция, получающая, хочет ли пользователь изменить данные пользователя"""
    if log(message):
        return

    if message.text.lower() == 'да':
        if message.from_user.id in GIRLS:
            send_message(message.from_user.id, 'Пизда')

        ask_data(message)
    else:
        send_message(message.from_user.id, 'Нет так нет')


def ask_data(message: Message):
    """Спрашивает пользователя, собирается ли он обедать в ближайший день"""
    send_message(message.from_user.id, f'Ты будешь обедать в {get_planning_day()}?',
                 reply_markup=make_bool_keyboard())
    bot.register_next_step_handler(message, get_data)


def get_data(message: Message):
    """Изначальная функция, получающая данные пользователя"""
    if log(message):
        return

    if message.text.lower() == 'да':
        users[message.from_user.id][DATA] = True
        dump(users, USERS)

        if message.from_user.id in GIRLS:
            send_message(message.from_user.id, 'Пизда')
        else:
            send_message(message.from_user.id, 'Записано!')

    elif message.text.lower() == 'нет':
        users[message.from_user.id][DATA] = False
        dump(users, USERS)

        send_message(message.from_user.id, 'А в школу пойдешь?', reply_markup=make_bool_keyboard())
        bot.register_next_step_handler(message, get_at_school)

    else:
        send_message(message.from_user.id, 'Этот бот немножко тупой. Чтобы он тебя понимал, пожалуйста, '
                                           'используй только ответы "да" и "нет".')
        bot.register_next_step_handler(message, get_data)


def get_at_school(message: Message):
    """Изначальная функция, получающая данные пользователя"""
    if log(message):
        return

    if message.text.lower() == 'да':
        users[message.from_user.id][VISIT] = True
        dump(users, USERS)

        send_message(message.from_user.id, 'Записано!')

    elif message.text.lower() == 'нет':
        users[message.from_user.id][VISIT] = False
        dump(users, USERS)

        send_message(message.from_user.id, 'Пожалуйста, укажи причину для твоего классного советника.',
                     reply_markup=make_keyboard([users[message.from_user.id][REASON] or '']))
        bot.register_next_step_handler(message, get_no_school_reason)

    else:
        send_message(message.from_user.id, 'Этот бот немножко тупой. Чтобы он тебя понимал, '
                                           'пожалуйста, используй только ответы "да" и "нет".')
        bot.register_next_step_handler(message, get_data)


def get_no_school_reason(message: Message):
    """"""
    if log(message):
        return

    if message.text.lower() == 'нет' or len(message.text) < 3:
        send_message(message.from_user.id, 'Ты че здесь, самый умный, да? А ну написал причину')
        bot.register_next_step_handler(message, get_no_school_reason)

    else:
        users[message.from_user.id][REASON] = message.text
        dump(users, USERS)

        send_message(message.from_user.id, 'Записано.')


def if_register(message: Message):
    """Нулевой этап регистрации пользователя"""
    if log(message):
        return

    if message.text.lower() == 'да':
        send_message(message.from_user.id, 'Выбери класс', reply_markup=make_keyboard(CLASSES))
        bot.register_next_step_handler(message, register)
    else:
        send_message(message.from_user.id, 'Нет так нет')


def register(message: Message):
    """Первый этап регистрации пользователя"""
    if log(message):
        return

    user_id = message.from_user.id
    current_class = message.text.capitalize()

    if current_class not in CLASSES:
        send_message(user_id, 'Нет такого класса',
                     reply_markup=make_keyboard(CLASSES))
        bot.register_next_step_handler(message, register)
        return

    if user_id in users[DELETED] and current_class != users[DELETED][user_id][CLASS]:
        send_message(user_id, 'Имей в виду, что классному советнику выбранного тобой класса '
                              'придет уведомление о твоей регистрации.')

    send_message(user_id, 'Введи фамилию и имя (так, чтоб классный советник понял, что это ты)',
                 reply_markup=make_keyboard([get_fullname(message)]))
    bot.register_next_step_handler(message, register_name, current_class)


def register_name(message: Message, class_letter):
    """Второй этап регистрации пользователя"""
    if log(message):
        return

    send_message(message.from_user.id, 'Зарегистрироваться?',
                 reply_markup=make_bool_keyboard())
    bot.register_next_step_handler(message, register_end, message.text, class_letter)


def register_end(message: Message, name, class_letter):
    """Последний этап регистрации пользователя"""
    if log(message):
        return

    global users

    if message.text.lower() == 'да':
        users[message.from_user.id] = {
            CLASS: class_letter,
            NAME: name,
            DATA: None
        }

        if message.from_user.id in users[DELETED]:
            del users[DELETED][message.from_user.id]

        users = dict(sorted(users.items(), key=lambda x: (x[0] == DELETED, float(x[0]) if x[0] != DELETED else 0)))
        dump(users, USERS)

        send_message(message.from_user.id, 'Ты успешно зарегистрирован!')

        try:
            send_message(CLASSES[class_letter], f'Ученик с id {message.from_user.id}, назвавшийся "{name}", '
                                                f'присоединился к вашему классу. Если это не ваш ученик, пожалуйста, '
                                                f'сообщите имя и id этого пользователя администратору @chmorodinka')
        except telebot.apihelper.ApiException:
            log(f'Классный советник класса {class_letter} не зарегистрирован!')

        send_message(message.from_user.id, 'Хочешь сразу внести данные?',
                     reply_markup=make_bool_keyboard())
        bot.register_next_step_handler(message, get_if_want_to_change_data)

    else:
        send_message(message.from_user.id, 'Регистрация отменена')


def send_notification():
    log('send_notification are called by schedule')
    for user_id in users:
        if users[user_id].get(DATA, False) is None:
            log(f'Отправка сообщения id{user_id} ({users[user_id][NAME]})')

            try:
                ask_data(make_empty_message(user_id))

            except Exception as error:
                if 'bot was blocked by the user' in str(error):
                    # del users[user_id]
                    error = f'Пользователь {users[user_id][NAME]} ({user_id}) заблокировал ' \
                            f'бота и (не) был удален.'
                    log(error)
                    send_message(MAKSIM, error)

                else:
                    log(error)


def send_report(clear=True, classes=CLASSES):
    log('send_report are called' + ' by schedule')
    for let in classes:
        cur_class = list(filter(lambda x: x.get(CLASS) == let, users.values()))

        text = no_data = lunch = no_lunch = no_school = ''
        k = [0] * 3

        for student in cur_class:
            if student[DATA] is None:
                no_data += student[NAME] + '\n'
            elif student[DATA]:
                lunch += student[NAME] + '\n'
                k[0] += 1
            elif student[VISIT]:
                no_lunch += student[NAME] + '\n'
                k[1] += 1
            else:
                no_school += f'{student[NAME]}: "{student[REASON] or "Причина не была указана."}"\n'
                k[2] += 1
            if clear:
                student[DATA] = student[VISIT] = None

        if lunch:
            text += f"В {get_planning_day()} {reform('будет', k[0])} обедать {k[0]} " \
                    f"{reform('ученик', k[0])} класса {let}:\n"
            text += lunch
        else:
            text += f"В {get_planning_day()} ни один ученик класса {let} не будет обедать.\n"

        if no_lunch:
            text += f"\nНе {reform('будет', k[1])} обедать, но " \
                    f"{reform('будет', k[1])} в школе {k[1]} {reform('ученик', k[1])}:\n"
            text += no_lunch

        if no_school:
            text += f"\nНе {reform('будет', k[2])} в школе {k[2]} {reform('ученик', k[2])}:\n"
            text += no_school

        if no_data:
            text += f"\nНе получено данных от:\n"
            text += no_data

        try:
            send_message(CLASSES[let], text)
        except telebot.apihelper.ApiException:
            log(f'Классный советник класса {let} не зарегистрирован!')


def run_schedule():
    schedule.every().day.at(MORNING_TIME).do(send_message, SOPHIA, 'Доброе утро, зайка, удачного дня💕')

    # Понедельник
    schedule.every().monday.at(MORNING_TIME).do(send_notification)
    schedule.every().monday.at(REPORT_TIME).do(send_report)
    schedule.every().monday.at(EVENING_TIME).do(send_notification)
    # Вторник
    schedule.every().tuesday.at(MORNING_TIME).do(send_notification)
    schedule.every().tuesday.at(REPORT_TIME).do(send_report)
    schedule.every().tuesday.at(EVENING_TIME).do(send_notification)
    # Среда
    schedule.every().wednesday.at(MORNING_TIME).do(send_notification)
    schedule.every().wednesday.at(REPORT_TIME).do(send_report)
    schedule.every().wednesday.at(EVENING_TIME).do(send_notification)
    # Четверг
    schedule.every().thursday.at(MORNING_TIME).do(send_notification)
    schedule.every().thursday.at(REPORT_TIME).do(send_report)
    schedule.every().thursday.at(EVENING_TIME).do(send_notification)
    # Пятница
    schedule.every().friday.at(MORNING_TIME).do(send_notification)
    schedule.every().friday.at(REPORT_TIME).do(send_report)
    schedule.every().friday.at(EVENING_TIME).do(send_notification)

    # Суббота
    schedule.every().saturday.at(MORNING_TIME).do(send_notification)
    schedule.every().saturday.at(REPORT_TIME).do(send_report)
    # Воскресенье
    schedule.every().sunday.at(EVENING_TIME).do(send_notification)

    log('Schedule started')
    while 1:
        try:
            schedule.run_pending()
        except Exception as error:
            log('schedule error - ' + str(error.__class__) + ' ' + str(error))
        # schedule.idle_seconds()
        sleep(1)


if __name__ == "__main__":
    schedule_thread = Thread(target=run_schedule)
    schedule_thread.start()
    send_message_thread = Thread(target=send_message_by_input)
    send_message_thread.start()
    log_text = None

    while 1:
        try:
            if log_text:
                send_message(MAKSIM, log_text)
            bot.polling(non_stop=True, skip_pending=True)
        except Exception as log_error:
            if isinstance(log_error, (requests.exceptions.ConnectionError,
                                      requests.exceptions.ReadTimeout,
                                      requests.exceptions.ConnectionError)):
                log('That annoying errors erroring again')
                log_text = None
            else:
                log_text = f'({log_error.__class__}, {log_error.__cause__}): {log_error}'
                log(log_text)
                log_text = f'{get_date()} - ' + log_text
                open(LOGS, 'a', encoding=ENCODING).write(log_text + '\n')
            sleep(5)

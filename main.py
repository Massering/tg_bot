import os
from time import sleep

from requests import exceptions
import schedule
from threading import Thread

import telebot

from engine import *
from config import *

if not os.path.exists(USERS):
    dump({DELETED: {}}, USERS)

users = json.load(open(USERS, 'r', encoding=ENCODING))
users = {i if i == DELETED else int(i): users[i] for i in users}
users[DELETED] = {int(i): users[DELETED][i] for i in users[DELETED]}

if not os.path.exists(STATISTIC):
    dump({STUDENT: [], CLASS: []}, STATISTIC)
statistic = json.load(open(STATISTIC, 'r', encoding=ENCODING))

bot = telebot.TeleBot(TOKEN)


def send_message(user_id: Union[int, str], text: str, reply_markup=None):
    text = str(text).strip()
    log((text, user_id))
    if isinstance(user_id, str):
        user_id = eval(user_id)
    bot.send_message(user_id, text, reply_markup=reply_markup)


def send_message_by_input():
    last_id = None
    while 1:
        s = input()
        if not s:
            continue

        try:
            user_id, *text = s.split()
        except UnicodeDecodeError:
            s1 = ''
            for i in s:
                try:
                    s1 += str(i.encode('CP866'), encoding='utf-8')
                except UnicodeDecodeError:
                    pass
            user_id, *text = s1.split()

        except Exception as error:
            log(f'Лох, как ты смог допустить ошибку "{error}"')
            continue

        try:
            send_message(user_id, ' '.join(text))
            last_id = user_id
        except (telebot.apihelper.ApiException, NameError, SyntaxError):  # Пользователя не существует
            if last_id:
                try:
                    send_message(last_id, ' '.join([user_id] + text))
                except Exception as error:
                    log(f'Лох, как ты смог допустить ошибку "{error}"')
        except Exception as error:
            log(f'Лох, как ты смог допустить ошибку "{error.__class__} - {error}"')


def log(message, starting=False, send_admin=False, to_file=False):
    """Вывод в консоль уведомления о сообщении боту + Проверка сообщения (выход)"""

    if send_admin:
        send_message(MAKSIM, str(message))
        send_message(SOPHIA, str(message))

    if to_file:
        open(LOGS, 'a', encoding='utf-8').write(f'{get_date()} - "{message}"\n')

    if isinstance(message, Message):
        name = get_fullname(message)
        name += f' (id {message.from_user.id})'
        text = f'{get_date()} - {name}: "{message.text}"'
        print(text)

        if 'я' in message.text.lower() and 'советник' in message.text.lower():
            send_message(MAKSIM, text)

        if message.text.lower() == '/exit':
            send_message(message.from_user.id, 'Выход из сценария')
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

    user_id = message.from_user.id

    if message.text == '/start':
        send_message(user_id, f'''
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
        send_message(user_id, 'Первое слово следующего сообщения будет использовано как id, а '
                              'остальные отправлены как текст.')
        bot.register_next_step_handler(message, send_message_by_id)

    elif message.text == '/my_id':
        send_message(user_id, str(user_id))

    elif user_id in CLASSES.values():
        *_, cur_class = sorted(i[0] for i in CLASSES.items() if i[1] == user_id)

        if message.text == '/my_class':
            text = 'Список учеников вашего класса:\n\n'
            students = [x for x in users if x != DELETED and users[x][CLASS] == cur_class]
            max_length = max(len(users[i][NAME]) for i in students)

            for n, student in enumerate(sorted(students, key=lambda x: users[x][NAME]), 1):
                name = users[student][NAME].ljust(max_length)
                name += ' ' * name.count(' ')
                text += f"{n}. {name}" + f' id {student}\n'

            send_message(user_id, text)

        elif message.text == '/report':
            send_report(clear=False, classes=[cur_class])

        else:
            send_message(user_id, TEACHER_COMMANDS)

    elif user_id not in users:
        send_message(user_id, 'Хочешь зарегистрироваться?',
                     reply_markup=make_bool_keyboard())
        bot.register_next_step_handler(message, if_register)

    elif message.text == '/permanently':
        if not users[user_id].get(ALWAYS):
            data = '\n'.join(f'{key}: {users[user_id][key]}' for key in [LUNCH, VISIT, REASON])
            send_message(user_id, f'''
Твои данные не будут очищаться ежедневно, но каждую неделю всё равно придется писать подтверждение боту.
Если ты не уверен, что всю неделю будешь следовать режиму, отключи эту функцию.
Отключить её можно в любой момент, написав /permanently

Проверь, чтобы введенные сейчас данные были именно такими, какими ты хочешь их оставить:
{data}

Ты уверен?''', reply_markup=make_bool_keyboard())
            bot.register_next_step_handler(message, make_permanently)

        else:
            send_message(user_id, 'Отключить функцию?', reply_markup=make_bool_keyboard())
            bot.register_next_step_handler(message, make_permanently)

    elif message.text == '/change_name':
        send_message(user_id, 'Введи новое имя. Имей в виду, что твой классный советник '
                              'будет уведомлен об изменении имени (/exit если вдруг передумал)',
                     reply_markup=make_keyboard({get_fullname(message), users[user_id][NAME]}))
        bot.register_next_step_handler(message, change_name)

    elif message.text == '/del_myself':
        send_message(user_id, 'Ты уверен, что хочешь удалить свои данные из системы?',
                     reply_markup=make_bool_keyboard())
        bot.register_next_step_handler(message, del_user)

    elif message.text == '/TV' and user_id in [SOPHIA, MAKSIM]:
        os.startfile(r'C:\Program Files\TeamViewer\TeamViewer.exe')

    elif message.text == '/mailing' and user_id in [SOPHIA, MAKSIM]:
        send_message(user_id, 'Введи сообщение, но будь аккуратен, это пошлётся всем',
                     reply_markup=make_bool_keyboard())
        bot.register_next_step_handler(message, mailing)

    else:
        if message.from_user.id in HUMANS:
            send_message(user_id, f'Veux {"enregistrer" * (users[user_id][LUNCH] is None) or "modifier"}'
                                  f' données pour demain?',
                         reply_markup=make_france_bool_keyboard())
        else:
            send_message(user_id, f'Хочешь {"записать" * (users[user_id][LUNCH] is None) or "изменить"}'
                                  f' данные {get_planning_day(need_date=False, na=True)}?',
                         reply_markup=make_bool_keyboard())
        bot.register_next_step_handler(message, get_if_want_to_change_data)


def mailing(message: Message):
    if log(message):
        return

    for student in users:
        # TODO:                                                СОЛНЦЕ
        # Подправь или вообще убери текст, если хочешь
        text = f'Сообщение от администратора всем пользователям:\n{message.text}'
        send_message(student, text)


def make_permanently(message: Message):
    if log(message):
        return

    data = users[message.from_user.id].get(ALWAYS, False)
    if message.text.lower() in POSITIVE:
        users[message.from_user.id][ALWAYS] = not data
        dump(users, USERS)

        send_message(message.from_user.id, 'Изменено.')

    elif message.text.lower() in NEGATIVE:
        send_message(message.from_user.id, ['Ну и славно)', 'Хорошо.'][data])

    else:
        send_message(message.from_user.id, 'Этот бот немножко тупой. Чтобы он тебя понимал, '
                                           'пожалуйста, используй только ответы "да" и "нет".')
        bot.register_next_step_handler(message, make_permanently)


def send_message_by_id(message: Message):
    if log(message):
        return

    try:
        user_id, *text = message.text.split()

        if message.from_user.id == MAKSIM:
            send_message(user_id, ' '.join(text))
        else:
            send_message(user_id, f'id {message.from_user.id}: \n{" ".join(text)}')

        send_message(message.from_user.id, f'Отправлено to id {user_id} "{" ".join(text)}"')

    except Exception as error:
        send_message(message.from_user.id, f'Лох, как ты смог допустить ошибку "{error.__class__} - {error}"')


def del_user(message: Message):
    """Функция, получающая, хочет ли пользователь удалить свои данные"""
    if log(message):
        return

    if message.text.lower() in POSITIVE:
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

    if message.text.lower() in POSITIVE:
        if message.from_user.id in GIRLS:
            send_message(message.from_user.id, 'Пизда')

        ask_lunch(message)
    else:
        if message.from_user.id in HUMANS:
            send_message(message.from_user.id, 'Non donc non')
        else:
            send_message(message.from_user.id, 'Нет так нет')


def ask_lunch(message: Message):
    """Спрашивает пользователя, собирается ли он обедать в ближайший день"""
    if message.from_user.id in HUMANS:
        send_message(message.from_user.id, f'Tu vas dîner demain {get_planning_day(need_weekday=0)}?',
                     reply_markup=make_france_bool_keyboard())
    else:
        send_message(message.from_user.id, f'Ты будешь обедать {get_planning_day()}?',
                     reply_markup=make_bool_keyboard())
    bot.register_next_step_handler(message, get_lunch)


def get_lunch(message: Message):
    """Изначальная функция, получающая данные пользователя"""
    if log(message):
        return

    if message.text.lower() in POSITIVE:
        users[message.from_user.id][LUNCH] = True
        dump(users, USERS)

        statistic[STUDENT].append((message.from_user.id, get_date(), dt.now().weekday() + 1, 1))
        dump(statistic, STATISTIC)

        if message.from_user.id in GIRLS:
            send_message(message.from_user.id, 'Пизда')

        if message.from_user.id in HUMANS:
            send_message(message.from_user.id, 'Enregistré!')
        else:
            send_message(message.from_user.id, 'Записано!')

    elif message.text.lower() in NEGATIVE:
        if message.from_user.id in HUMANS:
            send_message(message.from_user.id, "Et tu iras à l'école?", reply_markup=make_france_bool_keyboard())
        else:
            send_message(message.from_user.id, 'А в школу пойдешь?', reply_markup=make_bool_keyboard())
        bot.register_next_step_handler(message, get_at_school)

    else:
        send_message(message.from_user.id, 'Этот бот немножко тупой. Чтобы он тебя понимал, пожалуйста, '
                                           'используй только ответы "да" и "нет".')
        bot.register_next_step_handler(message, get_lunch)


def get_at_school(message: Message):
    """Изначальная функция, получающая данные пользователя"""
    if log(message):
        return

    if message.text.lower() in POSITIVE:
        users[message.from_user.id][LUNCH] = False
        users[message.from_user.id][VISIT] = True
        dump(users, USERS)

        statistic[STUDENT].append((message.from_user.id, get_date(), dt.now().weekday() + 1, 2))
        dump(statistic, STATISTIC)

        if message.from_user.id in HUMANS:
            send_message(message.from_user.id, 'Enregistré!')
        else:
            send_message(message.from_user.id, 'Записано!')

    elif message.text.lower() in NEGATIVE:
        users[message.from_user.id][LUNCH] = False
        users[message.from_user.id][VISIT] = False
        dump(users, USERS)

        statistic[STUDENT].append((message.from_user.id, get_date(), dt.now().weekday() + 1, 3))
        dump(statistic, STATISTIC)

        if message.from_user.id in HUMANS:
            send_message(message.from_user.id, "S'il vous plaît donner une raison pour votre conseiller de classe",
                         reply_markup=make_keyboard([users[message.from_user.id].get(REASON) or '']))
        else:
            send_message(message.from_user.id, 'Пожалуйста, укажи причину для твоего классного советника.',
                         reply_markup=make_keyboard([users[message.from_user.id].get(REASON) or '']))
        bot.register_next_step_handler(message, get_no_school_reason)

    else:
        send_message(message.from_user.id, 'Этот бот немножко тупой. Чтобы он тебя понимал, '
                                           'пожалуйста, используй только ответы "да" и "нет".')
        bot.register_next_step_handler(message, get_at_school)


def get_no_school_reason(message: Message):
    """"""
    if log(message):
        return

    if message.text.lower() in NEGATIVE or len(message.text) < 3:
        send_message(message.from_user.id, 'Ты че здесь, самый умный, да? А ну написал причину')
        bot.register_next_step_handler(message, get_no_school_reason)

    else:
        users[message.from_user.id][REASON] = message.text
        dump(users, USERS)

        if message.from_user.id in HUMANS:
            send_message(message.from_user.id, 'Enregistré!')
        else:
            send_message(message.from_user.id, 'Записано!')


def if_register(message: Message):
    """Нулевой этап регистрации пользователя"""
    if log(message):
        return

    if message.text.lower() in POSITIVE:
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

    names = {get_fullname(message)}
    if user_id in users[DELETED]:
        names.add(users[DELETED][user_id][NAME])

        if current_class != users[DELETED][user_id][CLASS]:
            send_message(user_id, 'Имей в виду, что классному советнику выбранного тобой класса '
                                  'придет уведомление о твоей регистрации.')

    send_message(user_id, 'Введи фамилию и имя (так, чтоб классный советник понял, что это ты)',
                 reply_markup=make_keyboard(names))
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

    if message.text.lower() in POSITIVE:
        users[message.from_user.id] = {
            CLASS: class_letter,
            NAME: name,
            LUNCH: None,
            VISIT: None,
            REASON: None
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

        send_message(message.from_user.id, f'Хочешь сразу записать данные {get_planning_day(na=True)}?',
                     reply_markup=make_bool_keyboard())
        bot.register_next_step_handler(message, get_if_want_to_change_data)

    else:
        send_message(message.from_user.id, 'Регистрация отменена')


def send_notification(morning=False):
    log('send_notification was called', send_admin=True)

    if morning and dt.now().date() != get_planning_day(formatted=False) or \
            not morning and (dt.now() + td(days=1)).date() != get_planning_day(formatted=False):
        log('send_notification was aborted', send_admin=True)
        return

    for user_id in users:
        if users[user_id].get(LUNCH, False) is None:
            try:
                ask_lunch(make_empty_message(user_id))

            except Exception as error:
                if 'bot was blocked by the user' in str(error):
                    # del users[user_id]
                    error = f'Пользователь {users[user_id][NAME]} ({user_id}) заблокировал ' \
                            f'бота и (не) был удален.'

                log(error, send_admin=True)


def send_report(clear=False, classes=CLASSES):
    log('send_report was called', send_admin=True)

    if len(classes) > 1 and dt.now().date() != get_planning_day(formatted=False, strong=True):
        log('send_report was aborted', send_admin=True)
        return

    for let in classes:
        cur_class = sorted(filter(lambda x: users[x].get(CLASS) == let, users), key=lambda x: users[x][NAME])

        text = no_data = lunch = no_lunch = no_school = ''
        k = [0] * 4

        for student in cur_class:
            if users[student][LUNCH] is None:
                k[0] += 1
                no_data += f'{k[0]}. {users[student][NAME]}\n'
            elif users[student][LUNCH]:
                k[1] += 1
                lunch += f'{k[1]}. {users[student][NAME]}\n'
            elif users[student][VISIT]:
                k[2] += 1
                no_lunch += f'{k[2]}. {users[student][NAME]}\n'
            else:
                k[3] += 1
                no_school += f'{k[3]}. {users[student][NAME]}: ' \
                             f'"{users[student].get(REASON) or "Причина не была указана."}"\n'
            if clear and not users[student].get(ALWAYS):
                users[student][LUNCH] = users[student][VISIT] = None
        dump(users, USERS)

        if k[1]:
            text += f"{get_planning_day().capitalize()} {reform('будет', k[1])} обедать {k[1]} " \
                    f"{reform('ученик', k[1])} класса {let}:\n"
            text += lunch
        else:
            text += f"{get_planning_day().capitalize()} ни один ученик класса {let} не будет обедать.\n"

        if k[2]:
            text += f"\nНе {reform('будет', k[2])} обедать, но " \
                    f"{reform('будет', k[2])} в школе {k[2]} {reform('ученик', k[2])}:\n"
            text += no_lunch

        if k[3]:
            text += f"\nНе {reform('будет', k[3])} в школе {k[3]} {reform('ученик', k[3])}:\n"
            text += no_school

        if k[0]:
            text += f"\nНе получено данных от:\n"
            text += no_data

        try:
            send_message(CLASSES[let], text)
            send_message(MAKSIM, text)
            send_message(SOPHIA, text)

            if clear:
                statistic[CLASS].append((let, get_date(), dt.now().weekday() + 1) + tuple(k))
                dump(format_json(statistic), STATISTIC)
        except telebot.apihelper.ApiException:
            log(f'Классный советник класса {let} не зарегистрирован!')


def send_notification_about_permanently():
    log('send_notification_about_permanently was called', send_admin=True)

    for student in users:
        if users[student].get(ALWAYS):
            send_message(student, 'Ты уверен, что всю следующую неделю будешь следовать режиму?',
                         reply_markup=make_bool_keyboard())
            bot.register_next_step_handler(make_empty_message(student), make_permanently)


def run_schedule():
    schedule.every().day.at(MORNING_TIME).do(send_message, SOPHIA, 'Доброе утро, солнце, удачного дня💕')
    schedule.every().day.at(MORNING_TIME).do(send_message, MAKSIM, 'Доброе утро, удачного дня.')
    schedule.every().day.at(MORNING_TIME).do(send_notification, morning=True)
    schedule.every().day.at(REPORT_TIME).do(send_report, clear=True)
    schedule.every().day.at(EVENING_TIME).do(send_notification)

    schedule.every().sunday.at(EVENING_TIME).do(send_notification_about_permanently)

    log('Schedule started')
    while 1:
        try:
            schedule.run_pending()
        except Exception as error:
            log('Schedule error: ' + str(error.__class__) + ' ' + str(error), send_admin=True, to_file=True)
        sleep(5)


if __name__ == "__main__":
    schedule_thread = Thread(target=run_schedule)
    schedule_thread.start()
    send_message_thread = Thread(target=send_message_by_input)
    send_message_thread.start()
    log_text = None

    while 1:
        try:
            bot.polling(non_stop=True, skip_pending=True)
        except Exception as log_error:
            if isinstance(log_error, (exceptions.ConnectionError,
                                      exceptions.ReadTimeout,
                                      exceptions.ConnectionError)):
                log('That annoying errors erroring again')
                log_text = None
            else:
                log_text = f'({log_error.__class__}, {log_error.__cause__}): {log_error}'
                log('Bot_polling error: ' + log_text, send_admin=True, to_file=True)
            sleep(5)

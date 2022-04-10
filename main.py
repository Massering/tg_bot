import os
from time import sleep

from requests import exceptions
import schedule
from threading import Thread

import telebot

from engine import *
from config import *

if not os.path.exists(USERS):
    dump({
        STUDENTS: {},
        DELETED: {}
    }, USERS)

users = json.load(open(USERS, 'r', encoding=ENCODING))
students = {int(i): users[STUDENTS][i] for i in users[STUDENTS]}
deleted = {int(i): users[DELETED][i] for i in users[DELETED]}

if not os.path.exists(STATISTIC):
    dump({STUDENTS: [], CLASSES: []}, STATISTIC)
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
            exec(s)
            continue
        except Exception:
            pass

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

    elif user_id in LETTERS.values():
        *_, letter = sorted(i[0] for i in LETTERS.items() if i[1] == user_id)

        if message.text == '/my_class':
            text = 'Список учеников вашего класса:\n\n'
            cur_class = [x for x in students if students[x][CLASS] == letter]
            max_length = max(len(students[i][NAME]) for i in cur_class)

            for n, student in enumerate(sorted(cur_class, key=lambda x: students[x][NAME]), 1):
                name = students[student][NAME].ljust(max_length)
                name += ' ' * name.count(' ')
                text += f"{n}. {name}" + f' id {student}\n'

            send_message(user_id, text)

        elif message.text == '/report':
            send_report(clear=False, classes=[letter])

        else:
            send_message(user_id, TEACHER_COMMANDS)

    elif user_id not in students:
        send_message(user_id, 'Хочешь зарегистрироваться?',
                     reply_markup=make_bool_keyboard())
        bot.register_next_step_handler(message, if_register)

    elif message.text == '/permanently':
        if not students[user_id].get(ALWAYS):
            data = '\n'.join(f'{key}: {students[user_id][key]}' for key in [LUNCH, VISIT, REASON])
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
                     reply_markup=make_keyboard({get_fullname(message), students[user_id][NAME]}))
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
        get_lunch(message)
        # if message.from_user.id in HUMANS:
        #     send_message(user_id, f'Veux {"enregistrer" * (students[user_id][LUNCH] is None) or "modifier"}'
        #                           f' données pour demain?',
        #                  reply_markup=make_france_bool_keyboard())
        # else:
        #     send_message(user_id, f'Хочешь {"записать" * (students[user_id][LUNCH] is None) or "изменить"}'
        #                           f' данные {get_planning_day(need_date=False, na=True)}?',
        #                  reply_markup=make_bool_keyboard())
        # bot.register_next_step_handler(message, get_if_want_to_change_data)


def mailing(message: Message):
    if log(message):
        return

    for student in students:
        send_message(student, message.text)


def make_permanently(message: Message):
    if log(message):
        return

    data = students[message.from_user.id].get(ALWAYS, False)
    if message.text.lower() in POSITIVE:
        students[message.from_user.id][ALWAYS] = not data
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
        deleted[message.from_user.id] = students[message.from_user.id].copy()
        del students[message.from_user.id]
        dump(users, USERS)

        send_message(message.from_user.id, 'Очень жаль, что ты покидаешь нас. Прощай')

    else:
        send_message(message.from_user.id, 'Ну и славно)')


def change_name(message: Message):
    """Функция, получающая, хочет ли пользователь удалить свои данные"""
    if log(message):
        return

    user = students[message.from_user.id]
    send_message(message.from_user.id, f'Имя {user[NAME]} изменено на {message.text}')
    send_message(LETTERS[user[CLASS]], f'Имя ученика {user[NAME]} было изменено на {message.text}')
    log(f'Имя ученика {user[NAME]} было изменено на {message.text}', send_admin=True)

    students[message.from_user.id][NAME] = message.text
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
        students[message.from_user.id][LUNCH] = True
        dump(users, USERS)

        statistic[STUDENTS].append((message.from_user.id, get_date(), dt.now().weekday() + 1, 1))
        dump(format_json(statistic), STATISTIC)

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
                                           'используй только ответы "Да" и "Нет".')


def get_at_school(message: Message):
    """Изначальная функция, получающая данные пользователя"""
    if log(message):
        return

    if message.text.lower() in POSITIVE:
        students[message.from_user.id][LUNCH] = False
        students[message.from_user.id][VISIT] = True
        dump(users, USERS)

        statistic[STUDENTS].append((message.from_user.id, get_date(), dt.now().weekday() + 1, 2))
        dump(format_json(statistic), STATISTIC)

        if message.from_user.id in HUMANS:
            send_message(message.from_user.id, 'Enregistré!')
        else:
            send_message(message.from_user.id, 'Записано!')

    elif message.text.lower() in NEGATIVE:
        students[message.from_user.id][LUNCH] = False
        students[message.from_user.id][VISIT] = False
        dump(users, USERS)

        statistic[STUDENTS].append((message.from_user.id, get_date(), dt.now().weekday() + 1, 3))
        dump(format_json(statistic), STATISTIC)

        if message.from_user.id in HUMANS:
            send_message(message.from_user.id, "S'il vous plaît donner une raison pour votre conseiller de classe",
                         reply_markup=make_keyboard([students[message.from_user.id].get(REASON) or '']))
        else:
            send_message(message.from_user.id, 'Пожалуйста, укажи причину для твоего классного советника.',
                         reply_markup=make_keyboard([students[message.from_user.id].get(REASON) or '']))
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
        students[message.from_user.id][REASON] = message.text
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
        send_message(message.from_user.id, 'Выбери класс', reply_markup=make_keyboard(LETTERS))
        bot.register_next_step_handler(message, register)
    else:
        send_message(message.from_user.id, 'Нет так нет')


def register(message: Message):
    """Первый этап регистрации пользователя"""
    if log(message):
        return

    user_id = message.from_user.id
    current_class = message.text.capitalize()

    if current_class not in LETTERS:
        send_message(user_id, 'Нет такого класса',
                     reply_markup=make_keyboard(LETTERS))
        bot.register_next_step_handler(message, register)
        return

    names = {get_fullname(message)}
    if user_id in deleted:
        names.add(deleted[user_id][NAME])

        if current_class != deleted[user_id][CLASS]:
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

    global students

    if message.text.lower() in POSITIVE:
        students[message.from_user.id] = {
            CLASS: class_letter,
            NAME: name,
            LUNCH: None,
            VISIT: None,
            REASON: None
        }

        if message.from_user.id in deleted:
            del deleted[message.from_user.id]

        d = dict(sorted(students.items(), key=lambda x: float(x[1][NAME])))
        students.clear()
        students += d

        dump(users, USERS)

        send_message(message.from_user.id, 'Ты успешно зарегистрирован!')

        try:
            send_message(LETTERS[class_letter], f'Ученик с id {message.from_user.id}, назвавшийся "{name}", '
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

    for user_id in students:
        if students[user_id].get(LUNCH, False) is None:
            try:
                ask_lunch(make_empty_message(user_id))

            except Exception as error:
                if 'bot was blocked by the user' in str(error):
                    # del students[user_id]
                    error = f'Пользователь {students[user_id][NAME]} ({user_id}) заблокировал ' \
                            f'бота и (не) был удален.'

                log(error, send_admin=True)


def send_report(clear=False, classes=LETTERS):
    log('send_report was called', send_admin=True)

    if len(classes) > 1 and dt.now().date() != get_planning_day(formatted=False, strong=True):
        log('send_report was aborted', send_admin=True)
        return

    for let in classes:
        cur_class = sorted(filter(lambda x: students[x].get(CLASS) == let, students), key=lambda x: students[x][NAME])

        text = no_data = lunch = no_lunch = no_school = ''
        k = [0] * 4

        for student in cur_class:
            if students[student][LUNCH] is None:
                k[0] += 1
                no_data += f'{k[0]}. {students[student][NAME]}\n'
            elif students[student][LUNCH]:
                k[1] += 1
                lunch += f'{k[1]}. {students[student][NAME]}\n'
            elif students[student][VISIT]:
                k[2] += 1
                no_lunch += f'{k[2]}. {students[student][NAME]}\n'
            else:
                k[3] += 1
                no_school += f'{k[3]}. {students[student][NAME]}: ' \
                             f'"{students[student].get(REASON) or "Причина не была указана."}"\n'
            if clear and not students[student].get(ALWAYS):
                students[student][LUNCH] = students[student][VISIT] = None
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
            send_message(LETTERS[let], text)
            send_message(MAKSIM, text)
            send_message(SOPHIA, text)

            if clear:
                statistic[CLASSES].append((let, get_date(), dt.now().weekday() + 1) + tuple(k))
                dump(format_json(statistic), STATISTIC)
        except telebot.apihelper.ApiException:
            log(f'Классный советник класса {let} не зарегистрирован!')


def send_notification_about_permanently():
    log('send_notification_about_permanently was called', send_admin=True)

    for student in students:
        if students[student].get(ALWAYS):
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

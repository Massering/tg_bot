import os
from time import sleep

# Чтобы адекватно называть получаемые ошибки, связанные с подключением
from requests import exceptions
# Всё действие во времени через библиотеку schedule
import schedule
# В программе используется разделение на потоки
from threading import Thread

# Сама библиотека взаимодействия с ботом
import telebot

# Функции и константы из других файлов
from engine import *
from config import *

# Открываем файл с зарегистрированными пользователями
# Из формата JSON он преобразуется сразу в словарь
if not os.path.exists(USERS):
    dump({
        STUDENTS: {},
        DELETED: {}
    }, USERS)

users = json.load(open(USERS, 'r', encoding=ENCODING))
students = {int(i): users[STUDENTS][i] for i in users[STUDENTS]}
deleted = {int(i): users[DELETED][i] for i in users[DELETED]}

# Открываем файл со статистикой
if not os.path.exists(STATISTIC):
    dump({STUDENTS: [], CLASSES: []}, STATISTIC)
statistic = json.load(open(STATISTIC, 'r', encoding=ENCODING))

# Создание бота по секретному токену
bot = telebot.TeleBot(TOKEN)


def send_message(user_id: int, text: str, reply_markup=None):
    """Функция, принимающая id пользователя и текст, который бот ему отправит. Создана для удобства"""
    text = text.strip()
    # Помечаем в консоль отправку
    log((text, user_id))
    bot.send_message(user_id, text, reply_markup=reply_markup)


def send_message_by_input():
    """Функция, созданная в отдельном потоке, пытающаяся выполнить команды из консоли прямо во время работы бота
    Также с её помощью можно отправлять сообщения по id"""
    last_id = None

    while 1:
        s = input()
        if not s:
            continue

        try:
            exec(s)
            continue
        except RuntimeError:
            pass

        # Очень сложная система, лучше вообще не возвращаться сюда
        # По возможности - стереть
        # Суть в том, чтобы работала консоль Линукса, в которой дурацкая CP866 кодировка
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
            log(f'Как ты смог допустить ошибку в "{error}"')
            continue

        try:
            send_message(eval(user_id), ' '.join(text))
            last_id = user_id
        except (telebot.apihelper.ApiException, NameError, SyntaxError):  # Пользователя не существует
            if last_id:
                try:
                    send_message(last_id, ' '.join([user_id] + text))
                except Exception as error:
                    log(f'Как ты смог допустить ошибку "{error}"')
        except Exception as error:
            log(f'Как ты смог допустить ошибку "{error.__class__} - {error}"')


def log(message, send_admin=False, to_file=False):
    """Вывод в консоль уведомления о сообщении боту + Проверка сообщения (на содержание команд и выход)"""

    if send_admin:
        # Уведомление админа личным сообщением в тг (о чем-то важном)
        for admin in ADMINS:
            send_message(admin, str(message))

    if to_file:
        # Запись в файл logs - для удобства логирования
        open(LOGS, 'a', encoding='utf-8').write(f'{get_date()} - "{message}"\n')

    # Для разных типов сообщений разный вывод
    if isinstance(message, Message):
        name = get_fullname(message)
        name += f' (id {message.from_user.id})'
        text = f'{get_date()} - {name}: "{message.text}"'
        print(text)

        if message.text.lower() == '/exit':
            send_message(message.from_user.id, 'Выход из сценария')
            return 1  # Это завершит функцию, из которой был вызван log

        if message.text[0] == '/' and message.text != '/start':  # Если содержит команду
            start(message)
            return 1

    elif isinstance(message, tuple):
        print(f'{get_date()} - this Bot to {message[1]}: "{message[0]}"')

    else:
        print(f'{get_date()} - system_log: "{message}"')


@bot.message_handler(content_types=['photo', 'document', 'audio'])
def f(message: Message):
    bot.forward_message(1089524173, message.from_user.id, message.id)
    send_message(message.from_user.id, 'Я не знаю, как с этим обращаться')


@bot.message_handler(content_types=['text'])
def start(message: Message):
    """Изначальная функция, принимающая команды пользователя"""
    log(message)

    user_id = message.from_user.id

    if message.text == '/start':  # В самом начале даём информацию о боте
        send_message(user_id, f'''
Приветствую тебя, мой друг!
Это бот, действующий в ФМШ СФУ, созданный для того, чтобы опрашивать учеников, будут ли они обедать
''')
        if user_id not in students:  # Если ученик не зарегистрирован, предлагаем сделать это
            send_message(user_id, 'Хочешь зарегистрироваться? (Если Вы - учитель, Вам тоже следует зарегистрироваться)',
                         reply_markup=make_bool_keyboard())
            bot.register_next_step_handler(message, if_register)
        else:
            send_message(user_id, 'Ты уже зарегистрирован в системе!', reply_markup=make_bool_keyboard())

    elif message.text == '/send_message':
        # Функция, чтобы отправлять другому пользователю сообщение, зная его id
        # Если честно, написал это, потому что было прикольно (как не побаловаться с тг-ботом)
        send_message(user_id, 'Первое слово следующего сообщения будет использовано как id, а '
                              'остальные отправлены как текст.')
        bot.register_next_step_handler(message, send_message_by_id)

    elif message.text == '/mailing' and user_id in ADMINS + [*LETTERS.values()]:
        # Рассылка от имени бота ВСЕМ зарегистрированным ученикам
        # Только для администраторов (и классных советников)
        send_message(user_id, 'Введи сообщение, но будь аккуратен, это пошлётся всем',
                     reply_markup=make_bool_keyboard())
        bot.register_next_step_handler(message, mailing)

    elif user_id in LETTERS.values():
        # Если пользователь классный советник, у него есть свои функции кроме вышеупомянутых
        *_, letter = sorted(i[0] for i in LETTERS.items() if i[1] == user_id)

        if message.text == '/my_class':
            # Получение списка учеников класса с id
            text = 'Список учеников Вашего класса:\n\n'
            cur_class = [x for x in students if students[x][CLASS] == letter]
            max_length = max(len(students[i][NAME]) for i in cur_class)

            for n, student in enumerate(sorted(cur_class, key=lambda x: students[x][NAME]), 1):
                name = students[student][NAME].ljust(max_length)
                name += ' ' * name.count(' ')
                text += f"{n}. {name}" + f' id {student}\n'

            send_message(user_id, text)

        elif message.text == '/report':
            # Отчёт вне расписания (посмотреть, кто уже отметился, а кто нет)
            send_report(classes=[letter])

        else:
            # Иначе даем список команд
            # Команды, которые получит учитель, если его команда не опознана
            send_message(user_id, '''
Список команд классных советников:
/my_class - получить список учеников моего класса
/report - получить информацию вневременно
''')

    elif user_id not in students:  # Если ученик не зарегистрирован, предлагаем сделать это
        send_message(user_id, 'Хочешь зарегистрироваться?',
                     reply_markup=make_bool_keyboard())
        bot.register_next_step_handler(message, if_register)

    elif message.text == '/permanently':
        # Функция для тех, кто не меняет свой выбор в течение недели
        # Всё равно опрашивает каждое воскресенье
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

    elif message.text == '/del_myself':
        # Удаление ученика из системы
        # Например, исключен из школы
        send_message(user_id, 'Ты уверен, что хочешь удалить свои данные из системы?',
                     reply_markup=make_bool_keyboard())
        bot.register_next_step_handler(message, del_user)

    else:
        get_lunch(message, from_start=True)

        # Раньше здесь было переспрашивание ученика, но потом я увидел, что ученики не замечают на этот вопрос
        # Так что я сделал в любом случае просто запись (либо бот скажет, что не понимает)
        #
        # send_message(user_id, f'Хочешь {"записать" * (students[user_id][LUNCH] is None) or "изменить"} данные '
        #                       f'{get_planning_day(need_date=False, na=True)}?', reply_markup=make_bool_keyboard())
        # bot.register_next_step_handler(message, get_if_want_to_change_data)


def mailing(message: Message):
    """Рассылка ВСЕМ ученикам"""
    if log(message):  # Если сообщение содержит информацию о выходе, прекращаем работу
        return

    # Можно добавить фильтр по классам...
    for student in students:
        send_message(student, message.text)


def make_permanently(message: Message):
    """Добавляет свойство неизменности данных ученика"""
    if log(message):
        return

    data = students[message.from_user.id].get(ALWAYS, False)  # То, что установлено сейчас
    if message.text.lower() in POSITIVE:
        students[message.from_user.id][ALWAYS] = not data
        dump(users, USERS)

        send_message(message.from_user.id, 'Изменено.')

    elif message.text.lower() in NEGATIVE:  # не включил  /  оставил
        send_message(message.from_user.id, ['Ну и славно)', 'Хорошо.'][data])

    else:
        send_message(message.from_user.id, 'Чтобы бот тебя понимал, пожалуйста, используй только ответы "да" и "нет".')
        bot.register_next_step_handler(message, make_permanently)


def send_message_by_id(message: Message):
    """Функция отправляет пользователю сообщение от другого пользователя через бота"""
    if log(message):
        return

    try:
        user_id, *text = message.text.split()

        if message.from_user.id in ADMINS:
            # У админов свои привилегии...
            send_message(user_id, ' '.join(text))
        else:
            send_message(user_id, f'id {message.from_user.id}: \n{" ".join(text)}')

        send_message(message.from_user.id, f'Отправлено to id {user_id} "{" ".join(text)}"')

    except Exception as error:
        send_message(message.from_user.id, f'Ошибка в id "{error.__class__} - {error}"')


def del_user(message: Message):
    """Функция, получающая, хочет ли пользователь удалить свои данные"""
    if log(message):
        return

    if message.text.lower() in POSITIVE:
        deleted[message.from_user.id] = students[message.from_user.id].copy()
        del students[message.from_user.id]

        # Перезапись файла (приходится перезаписывать всех учеников)
        users[STUDENTS] = students
        users[DELETED] = deleted
        dump(users, USERS)

        send_message(message.from_user.id, 'Очень жаль, что ты покидаешь нас. Прощай')

    else:
        send_message(message.from_user.id, 'Ну и славно)')


def ask_lunch(message: Message):
    """Напоминание, спрашивает пользователя, собирается ли он обедать в ближайший день"""
    send_message(message.from_user.id, f'Ты будешь обедать {get_planning_day()}?',
                 reply_markup=make_bool_keyboard())
    bot.register_next_step_handler(message, get_lunch)


def get_lunch(message: Message, from_start=False):
    """Функция, получающая ответ пользователя, и записывающее данные + статистику"""
    if not from_start and log(message):  # from_start просто чтобы не выводило лог во второй раз
        return

    if message.text.lower() in POSITIVE:
        # Запись данных
        students[message.from_user.id][LUNCH] = True
        dump(users, USERS)

        # Запись статистики (id, дата, день недели, режим (1 - буду обедать))
        # statistic[STUDENTS].append((message.from_user.id, get_date(), dt.now().weekday() + 1, 1))
        # dump(format_json(statistic), STATISTIC)

        send_message(message.from_user.id, 'Записано!')

    elif message.text.lower() in NEGATIVE:
        # Если не будет обедать, возможно, ученик не пойдет в школу
        # Уточним это, чтобы затем доложить классному советнику
        send_message(message.from_user.id, 'А в школу пойдешь?', reply_markup=make_bool_keyboard())
        bot.register_next_step_handler(message, get_at_school)

    else:
        # Бот не понял ответа
        send_message(message.from_user.id, f'Пиши "Да", если будешь обедать {get_planning_day()} и "Нет" иначе',
                     reply_markup=make_bool_keyboard())


def get_at_school(message: Message):
    """Получающая, пойдет ли ученик в школу"""
    if log(message):
        return

    if message.text.lower() in POSITIVE:
        students[message.from_user.id][LUNCH] = False
        students[message.from_user.id][VISIT] = True
        dump(users, USERS)

        # Запись статистики (id, дата, день недели, режим (2 - не буду обедать, но буду в школе))
        # statistic[STUDENTS].append((message.from_user.id, get_date(), dt.now().weekday() + 1, 2))
        # dump(format_json(statistic), STATISTIC)

        send_message(message.from_user.id, 'Записано!')

    elif message.text.lower() in NEGATIVE:
        students[message.from_user.id][LUNCH] = False
        students[message.from_user.id][VISIT] = False
        dump(users, USERS)

        # Запись статистики (id, дата, день недели, режим (3 - не буду в школе, соответственно не буду обедать))
        # statistic[STUDENTS].append((message.from_user.id, get_date(), dt.now().weekday() + 1, 3))
        # dump(format_json(statistic), STATISTIC)

        send_message(message.from_user.id, 'Пожалуйста, укажи причину для твоего классного советника.',
                     reply_markup=make_keyboard([students[message.from_user.id].get(REASON) or '']))
        bot.register_next_step_handler(message, get_no_school_reason)

    else:
        send_message(message.from_user.id, 'Чтобы бот тебя понимал, пожалуйста, используй только ответы "да" и "нет".')
        bot.register_next_step_handler(message, get_at_school)


def get_no_school_reason(message: Message):
    """Получает причину, почему ученик не пойдет в школу"""
    if log(message):
        return

    if message.text.lower() in NEGATIVE + POSITIVE or len(message.text) < 3:
        # Заставим написать настоящую причину + защита от случайного нажатия (Да -> Да -> Да)
        send_message(message.from_user.id, 'Я не верю, что это причина, пожалуйста, не ври мне')
        bot.register_next_step_handler(message, get_no_school_reason)

    else:
        students[message.from_user.id][REASON] = message.text
        dump(users, USERS)

        send_message(message.from_user.id, 'Записано!')


def if_register(message: Message):
    """Нулевой этап регистрации пользователя, принимает "Да" и "Нет" """
    if log(message):
        return

    if message.text.lower() in POSITIVE:  # Если пользователь согласен зарегистрироваться
        # Для классных советников отдельный класс (надеюсь, ученики не будут выбирать его)
        send_message(message.from_user.id, 'Выбери класс',
                     reply_markup=make_keyboard(['Я - классный советник'] + [*LETTERS]))
        bot.register_next_step_handler(message, register)
    else:
        send_message(message.from_user.id, 'Нет так нет')


def register(message: Message, class_management=False):
    """Первый этап регистрации пользователя, принимает букву класса"""
    if log(message):
        return

    # Зададим значения, чтобы не писать каждый раз
    user_id = message.from_user.id
    current_class = message.text

    if class_management:
        # Выбор для тех, кто сказал, что он классный советник в прошлый раз
        name = get_fullname(message) + f' (id {message.from_user.id})'
        log(f'Пользователь {name} утверждает, что он советник класса {current_class}', send_admin=True)
        send_message(user_id, 'Спасибо, Ваш id был отправлен администратору.')
        return

    if current_class == 'Я - классный советник':
        # Предлагаем выбрать класс "управления"
        send_message(user_id, 'Пожалуйста, введите, каким классом Вы повелеваете', reply_markup=make_keyboard(LETTERS))
        bot.register_next_step_handler(message, register, class_management=True)
        return

    if current_class not in LETTERS:
        send_message(user_id, 'Такого класса не найдено. Попробуй ещё раз',
                     reply_markup=make_keyboard([*LETTERS] + ['Классные советники']))
        bot.register_next_step_handler(message, register)
        return

    # Имя пользователя в Телеграм и, если есть, от прошлой регистрации
    names = {get_fullname(message)}
    if user_id in deleted:
        names.add(deleted[user_id][NAME])

        # Значит, пользователь хочет перейти в другой класс
        # Оповестим об этом классного советника. Защита от хулиганов
        if current_class != deleted[user_id][CLASS]:
            send_message(user_id, 'Имей в виду, что классному советнику выбранного тобой класса '
                                  'придет уведомление о твоей регистрации.')

    # Просим фамилию и имя, чтобы классный советник мог различать учеников
    send_message(user_id, 'Введи фамилию и имя (так, чтоб классный советник понял, что это ты)',
                 reply_markup=make_keyboard(names))
    bot.register_next_step_handler(message, register_name, current_class)


def register_name(message: Message, class_letter):
    """Второй этап регистрации пользователя, принимает имя пользователя"""
    if log(message):
        return

    # Переспрашиваем, зарегистрироваться ли
    send_message(message.from_user.id, 'Зарегистрироваться?',
                 reply_markup=make_bool_keyboard())
    bot.register_next_step_handler(message, register_end, message.text, class_letter)


def register_end(message: Message, name: str, class_letter: str):
    """Последний этап регистрации пользователя, принимает "Да" и "Нет" """
    if log(message):
        return

    global students

    if message.text.lower() in POSITIVE:
        # Добавляем пользователя в словарь
        students[message.from_user.id] = {
            CLASS: class_letter,
            NAME: name,
            LUNCH: None,
            VISIT: None,
            REASON: None
        }

        if message.from_user.id in deleted:  # Удаляем из удаленных, если ученик там был
            del deleted[message.from_user.id]

        users[STUDENTS] = students = dict(sorted(students.items(), key=lambda x: x[1][NAME]))
        users[DELETED] = deleted
        dump(users, USERS)

        send_message(message.from_user.id, 'Ты успешно зарегистрирован!')

        try:
            # В любом случае оповещаем классного советника о том, что такой-то ученик присоединился к классу
            send_message(LETTERS[class_letter], f'Ученик с id {message.from_user.id}, назвавшийся "{name}", '
                                                f'присоединился к Вашему классу. Если это не Ваш ученик, пожалуйста, '
                                                f'сообщите имя и id этого пользователя администратору @chmorodina')
        except telebot.apihelper.ApiException:
            log(f'Классный советник класса {class_letter} не зарегистрирован!', send_admin=True)

    elif message.text.lower() in NEGATIVE:
        send_message(message.from_user.id, 'Регистрация отменена')
    else:
        send_message(message.from_user.id, 'Чтобы бот тебя понимал, пожалуйста, используй только ответы "да" и "нет"')


def send_notification(morning=False, friday=False):
    """Функция оповещения учеников, всё ещё не сделавших свой выбор (по вечерам это почти все)"""
    log('send_notification was called', send_admin=True)  # Оповещаем админа (допустимо отключить...)

    # Эта жуть здесь, чтобы функция не вызывалась по праздникам и выходным. Хорошо бы переделать...
    if (not friday and morning and dt.now().date() != get_planning_day(formatted=False)) or \
            (not morning and (dt.now() + td(days=1)).date() != get_planning_day(formatted=False)):
        log('send_notification was aborted', send_admin=True)
        return

    for student in students:
        if students[student][LUNCH] is None:  # Если ничего не указано, пишем, иначе - не тревожим
            try:
                ask_lunch(make_empty_message(student))

            except Exception as error:
                if 'bot was blocked by the user' in str(error):  # Ситуация плохая, надеемся, такого не случится
                    # del students[user_id]
                    error = f'Пользователь {students[student][NAME]} ({student}) заблокировал ' \
                            f'бота и (не) был удален.'

                log(error, send_admin=True)


def send_report(classes=LETTERS):
    """Функция отправки классным руководителям отчета на грядущий день"""
    if len(classes) == 1:
        # В том случае, если функцию вызывает классный советник, она только для одного класса
        log(f'send_report for {classes[0]} was called', send_admin=True)
        clear = False

    else:
        log('send_report was called', send_admin=True)
        clear = True

        # Опять же, чтобы не вызывалось по выходным и праздникам
        planning_day = get_planning_day(formatted=False).strftime("%d.%m")
        if planning_day in HOLIDAYS:
            log(f'send_report was aborted because {planning_day} in holidays', send_admin=True)
            return

    for let in classes:
        # Список id учеников класса
        cur_class = sorted([x for x in students if students[x][CLASS] == let], key=lambda x: students[x][NAME])

        text = no_data = lunch = no_lunch = no_school = ''
        data = [0] * 4  # Количество людей [Нет данных, Будет обедать, Будет в школе, Не будет в школе]

        for student in cur_class:
            if students[student][LUNCH] is None:  # Нет данных
                data[0] += 1
                no_data += f'{data[0]}. {students[student][NAME]}\n'
                send_message(students[student], f'Извините, но вы не успели ответить. Вы не будете кушать '
                                                f'{get_planning_day(need_date=False, need_weekday=True)}')

            elif students[student][LUNCH]:  # Будет обедать
                data[1] += 1
                lunch += f'{data[1]}. {students[student][NAME]}\n'

            elif students[student][VISIT]:  # Будет в школе
                data[2] += 1
                no_lunch += f'{data[2]}. {students[student][NAME]}\n'

            else:  # Не будет в школе
                data[3] += 1
                no_school += f'{data[3]}. {students[student][NAME]}: ' \
                             f'"{students[student].get(REASON) or "Причина не была указана."}"\n'  # Вот он пёс

            if clear and not students[student].get(ALWAYS):  # Если у ученика не включена функция permanently
                students[student][LUNCH] = students[student][VISIT] = None
                # Причину не очищаем, чтобы ученику не приходилось вводить её каждый раз

        # Формирование красивого списка для классного руководителя
        if data[1]:
            text += f"{get_planning_day().capitalize()} {reform('будут', data[1])} обедать {data[1]} " \
                    f"{reform('ученик', data[1])} класса {let}:\n"
            text += lunch
        else:
            text += f"{get_planning_day().capitalize()} ни один ученик класса {let} не будет обедать.\n"

        if data[2]:
            text += f"\nНе {reform('будет', data[2])} обедать, но " \
                    f"{reform('будет', data[2])} в школе {data[2]} {reform('ученик', data[2])}:\n"
            text += no_lunch

        if data[3]:
            text += f"\nНе {reform('будет', data[3])} в школе {data[3]} {reform('ученик', data[3])}:\n"
            text += no_school

        if data[0]:
            text += f"\nНе получено данных от:\n"
            text += no_data

        try:
            send_message(LETTERS[let], text)
            for admin in ADMINS:  # Здесь он дублирует это админам, было очень важно на стадии отладки
                send_message(admin, text)

            if clear:
                statistic[CLASSES].append((let, get_date(), dt.now().weekday() + 1) + tuple(data))
                dump(format_json(statistic), STATISTIC)
        except telebot.apihelper.ApiException:
            log(f'Классный советник класса {let} не зарегистрирован!', send_admin=True)

    # В конце записываем изменения (очистку внесенных данных)
    dump(users, USERS)


def send_notification_about_permanently():
    """Отправляет напоминание о своём существовании людям, которые пользуются функцией permanently"""
    log('send_notification_about_permanently was called', send_admin=True)

    for student in students:
        if students[student].get(ALWAYS):
            try:
                send_message(student, 'Ты уверен, что всю следующую неделю будешь следовать режиму?',
                             reply_markup=make_bool_keyboard())
                bot.register_next_step_handler(make_empty_message(student), make_permanently)

            except Exception as error:
                if 'bot was blocked by the user' in str(error):  # Ситуация плохая, надеемся, такого не случится
                    # del students[user_id]
                    error = f'Пользователь {students[student][NAME]} ({student}) заблокировал ' \
                            f'бота и (не) был удален.'

                log(error, send_admin=True)


def run_schedule():
    """Функция, настраивающая библиотеку schedule, напоминания и отчёты"""
    # Не ругаися насяника
    schedule.every().day.at(MORNING_TIME).do(send_message, ADMINS[0], 'Доброе утро, господин, удачного дня')

    # Понедельник
    schedule.every().monday.at(MORNING_TIME).do(send_notification, morning=True)
    schedule.every().monday.at(REPORT_TIME).do(send_report)
    schedule.every().monday.at(EVENING_TIME).do(send_notification)

    # Вторник
    schedule.every().tuesday.at(MORNING_TIME).do(send_notification, morning=True)
    schedule.every().tuesday.at(REPORT_TIME).do(send_report)
    schedule.every().tuesday.at(EVENING_TIME).do(send_notification)

    # Среда
    schedule.every().wednesday.at(MORNING_TIME).do(send_notification, morning=True)
    schedule.every().wednesday.at(REPORT_TIME).do(send_report)
    schedule.every().wednesday.at(EVENING_TIME).do(send_notification)

    # Четверг
    schedule.every().thursday.at(MORNING_TIME).do(send_notification, morning=True)
    schedule.every().thursday.at(REPORT_TIME).do(send_report)
    schedule.every().thursday.at(EVENING_TIME).do(send_notification)

    # Пятница
    schedule.every().friday.at(MORNING_TIME).do(send_notification, morning=True)
    schedule.every().friday.at(REPORT_TIME).do(send_report)
    schedule.every().friday.at(EVENING_TIME).do(send_notification)

    # Суббота
    schedule.every().saturday.at(MORNING_TIME).do(send_notification, morning=True)
    schedule.every().saturday.at(REPORT_TIME).do(send_report)
    schedule.every().saturday.at(EVENING_TIME).do(send_notification)

    # Функция permanently
    schedule.every().sunday.at(EVENING_TIME).do(send_notification_about_permanently)

    # Помечаем время и то, что всё прошло успешно
    log('Schedule started', to_file=True)
    while 1:
        try:
            schedule.run_pending()
        except Exception as error:
            # Это печально, потому что библиотека в случае ошибки не посчитает действие выполненным
            # И будет вызывать функцию с ошибкой до тех пор, пока не получится
            # Всё это время бедному админу будут приходить сообщения об этом
            log('Schedule error: ' + str(error.__class__) + ' ' + str(error), send_admin=True, to_file=True)
        sleep(30)  # Остановка (в пределах потока) на отдых


if __name__ == "__main__":
    # Поток библиотеки schedule
    schedule_thread = Thread(target=run_schedule)
    schedule_thread.start()

    # Поток, принимающий из консоли команды
    send_message_by_input_thread = Thread(target=send_message_by_input)
    send_message_by_input_thread.start()

    while 1:
        try:
            # Запускаем бота
            bot.polling(non_stop=True, skip_pending=True)

        except Exception as log_error:
            if isinstance(log_error, exceptions.ReadTimeout):
                # Такие ошибки могут появляться регулярно
                # Я читал, их возникновение связано с ошибками в библиотеке telebot
                log('That annoying errors erroring again')

            elif isinstance(log_error, exceptions.ConnectionError):
                # Такое чаще всего при отсутствии подключения к интернету
                log('Ошибка соединения. Проверьте подключение к интернету', send_admin=True)

            else:
                # Иначе отправляем админу, чтобы он разбирался
                log('Polling error: ' + f'({log_error.__class__}, {log_error.__cause__}): {log_error}',
                    send_admin=True, to_file=True)
            sleep(5)

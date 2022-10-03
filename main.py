import os
from time import sleep

# Чтобы адекватно называть получаемые ошибки, связанные с подключением
from requests import exceptions
# Всё действие во времени через библиотеку schedule
import schedule
# В программе используется разделение на потоки
from threading import Thread
# Реализованная идея с разными ответами
from random import choice

# Сама библиотека взаимодействия с ботом
import telebot

# Функции и константы из других файлов
from engine import *
from config import *

# Открываем файл с зарегистрированными пользователями
# Из формата JSON он преобразуется сразу в словарь
if not os.path.exists(USERS):
    print(f'File {USERS} does not exists!!!')
    dump({
        STUDENTS: {},
        DELETED: {},
        CLASSES: {}
    }, USERS)

users = json.load(open(USERS, 'r', encoding=ENCODING))
students = {int(i): users[STUDENTS][i] for i in users[STUDENTS]}
deleted = {int(i): users[DELETED][i] for i in users[DELETED]}
LETTERS = {i: users[CLASSES][i] for i in users[CLASSES]}

# Создание бота по секретному токену
bot = telebot.TeleBot(TOKEN)


def send_message(user_id: int, text: Union[str, list], reply_markup=None):
    """Функция, принимающая id пользователя и текст, который бот ему отправит. Создана для удобства"""
    if isinstance(text, list):
        text = choice(text)
    text = text.strip()

    # Помечаем в консоль отправку
    log((text, user_id))

    while 1:
        try:
            bot.send_message(user_id, text, reply_markup=reply_markup)
            break
        except Exception as error:
            if 'Failed to establish a new connection' in str(error):
                error = 'Из-за отключения интернета бот не может отправить сообщение'
                log(error, to_file=True)
                sleep(30)
            else:
                if 'bot was blocked by the user' in str(error):  # Ситуация плохая, надеемся, такого не случится
                    # del students[user_id]
                    error = f'Пользователь {get_fullname(user_id, True, True)} заблокировал ' \
                            f'бота и (не) был удален.'
                elif 'chat not found' in str(error):
                    if user_id in students:
                        error = f'Ученик {get_fullname(user_id, True, True)}'
                    elif user_id in LETTERS.values():
                        error = f'Учитель id {user_id} класса {get_letter(user_id)}'
                    else:
                        error = f'Пользователь {get_fullname(user_id, True, True)}'
                    error += f' всё ещё не написал боту!'
                log(error, send_admin=True)
                break


def get_fullname(obj: Union[Message, int, str], need_id=False, need_class=False) -> str:
    """Возвращает ФИ пользователя, под которыми он зарегистрирован в Телеграмм"""
    if type(obj) == Message:
        user_id = obj.from_user.id
    else:
        user_id = int(obj)

    if user_id in students:
        name = students[user_id][NAME] + (', ' + students[user_id][CLASS]) * need_class
    elif type(obj) == Message:
        name = (obj.from_user.last_name or ' ') + ' ' + obj.from_user.first_name
    elif user_id in LETTERS.values():
        name = f'Лорд класса {get_letter(user_id)}'
    else:
        name = str(user_id)

    return name.strip().title() + f' (id {user_id})' * need_id


def get_letter(senior: int):
    for let in LETTERS:
        if LETTERS[let] == senior:
            return let
    return 'Unknown'


def send_message_by_input():
    """Функция, созданная в отдельном потоке, пытающаяся выполнить команды из консоли прямо во время работы бота
    Также с её помощью можно отправлять сообщения по id"""
    last_id = 0
    user_id = text = ''

    while 1:
        s = input() + ' '
        if not s:
            continue

        try:
            exec(s)
            print('Команда выполнена успешно!')
        except Exception as error:
            print('ERROR:', error)

        # Очень сложная система, лучше вообще не возвращаться сюда
        # По возможности - стереть
        # Суть в том, чтобы работала консоль Линукса, в которой дурацкая CP866 кодировка
        try:
            user_id, text = s.split(maxsplit=1)
        except UnicodeDecodeError:
            try:
                s1 = str(s.encode('CP866'), encoding=ENCODING)
                user_id, text = s1.split(maxsplit=1)
            except UnicodeDecodeError:
                pass

        except Exception as error:
            log(f'Как ты смог допустить ошибку в "{error}"')
            continue

        try:
            send_message(eval(user_id), text)
            last_id = user_id
        except (telebot.apihelper.ApiException, NameError, SyntaxError):  # Пользователя не существует
            if last_id:
                try:
                    send_message(last_id, s)
                except Exception as error:
                    log(f'Как ты смог допустить ошибку "{error}"')
        except Exception as error:
            log(f'Как ты смог допустить ошибку "{error.__class__} - {error}"')


def log(message, send_admin=False, to_file=False, from_start=False):
    """Вывод в консоль уведомления о сообщении боту + Проверка сообщения (на содержание команд и выход)"""

    if send_admin:
        # Уведомление админа личным сообщением в тг (о чем-то важном)
        for admin in ADMINS:
            send_message(admin, str(message))

    if to_file:
        # Запись в файл logs - для удобства логирования
        with open(LOGS, 'a', encoding='utf-8') as log_file:
            log_file.write(f'{get_date()} - "{message}"\n')

    # Для разных типов сообщений разный вывод
    if isinstance(message, Message):
        if message.text is None:
            start_with_media(message)
            return 1

        name = get_fullname(message, True, True)
        text = f'{get_date()} - {name}: "{message.text}"'
        print(text)

        if from_start:
            return

        if message.text.lower() == '/exit':
            send_message(message.chat.id, 'Выход из сценария')
            return 1  # Это завершит функцию, из которой был вызван log

        if message.text[0] == '/' and message.text != '/start':  # Если содержит команду
            start(message)
            return 1

    elif isinstance(message, tuple):
        print(f'{get_date()} - this Bot to {get_fullname(message[1])}: "{message[0]}"')

    else:
        print(f'{get_date()} - system_log: "{message}"')


@bot.message_handler(content_types=['photo', 'document', 'audio'])
def start_with_media(message: Message):
    bot.forward_message(ADMINS[0], message.chat.id, message.id)
    send_message(message.chat.id, 'Я не знаю, как с этим обращаться')


@bot.message_handler(content_types=['text'])
def start(message: Message):
    """Изначальная функция, принимающая команды пользователя"""
    log(message, from_start=True)

    user_id = message.from_user.id
    chat_id = message.chat.id

    if user_id == 1946021974:
        bot.forward_message(ADMINS[0], message.chat.id, message.id)

    if message.text == '/start':  # В самом начале даём информацию о боте
        send_message(chat_id, f'''
Приветствую тебя, мой друг!
Это бот, действующий в ФМШ СФУ, созданный для того, чтобы опрашивать учеников, будут ли они обедать
''')
        if user_id not in students:  # Если ученик не зарегистрирован, предлагаем сделать это
            send_message(chat_id, 'Хочешь зарегистрироваться? (Если Вы - учитель, Вам тоже следует зарегистрироваться)',
                         reply_markup=bool_keyboard())
            bot.register_next_step_handler(message, if_register)
        else:
            send_message(chat_id, 'Ты уже зарегистрирован в системе!')

    elif message.text == '/send_message':
        # Функция, чтобы отправлять другому пользователю сообщение, зная его id или имя
        send_message(chat_id, 'Введи id или точное имя пользователя')
        bot.register_next_step_handler(message, send_message_by_id)

    elif message.text == '/mailing' and user_id in ADMINS + [*LETTERS.values()]:
        # Рассылка от имени бота ВСЕМ зарегистрированным ученикам
        # Только для администраторов (и классных советников)
        send_message(chat_id, 'Введите сообщение. Будьте аккуратны, это сообщение будет отправлено всем Вашим ученикам')
        bot.register_next_step_handler(message, mailing)

    elif '/make_lord' in message.text.lower() and user_id in ADMINS:
        lord_id, class_letter = message.text.split(maxsplit=1)[1].split('=')
        make_lord(lord_id, class_letter)

    elif user_id in LETTERS.values():
        # Если пользователь - классный советник, у него есть свои функции кроме вышеупомянутых
        *_, letter = sorted(i[0] for i in LETTERS.items() if i[1] == user_id)
        cur_class = sorted([i for i in students if students[i][CLASS] == letter], key=lambda x: students[x][NAME])
        class_list = [students[i][NAME] for i in cur_class]
        bot.forward_message(ADMINS[0], message.from_user.id, message.id)

        if message.text == '/my_class':
            # Получение списка учеников класса с id
            if cur_class:
                text = 'Список учеников Вашего класса:\n\n'
                max_length = max(len(students[i][NAME]) for i in cur_class)

                for n, student in enumerate(cur_class, 1):
                    name = students[student][NAME].ljust(max_length)
                    name += ' ' * name.count(' ')
                    text += f"{n}. {name}" + f' id {student}\n'
            else:
                text = 'В Вашем классе пока нет учеников'

            send_message(chat_id, text)

        elif message.text == '/report':
            # Отчёт вне расписания (посмотреть, кто уже отметился, а кто нет)
            send_report(letter=letter)

        elif message.text == '/rename':
            send_message(chat_id, 'Выберите из списка имя того, кого хотите переименовать',
                         reply_markup=class_list)
            bot.register_next_step_handler(message, rename, cur_class)

        elif message.text == '/del_student':
            send_message(chat_id, 'Выберите из списка имя того, кого хотите удалить',
                         reply_markup=class_list)
            bot.register_next_step_handler(message, del_user, cur_class)

        else:
            # Иначе даем список команд
            # Команды, которые получит учитель, если его команда не опознана
            send_message(chat_id, '''
Список команд классных советников:
/my_class - получить список зарегистрированных учеников моего класса
/report - получить отчет о собранной на данный момент информации
/mailing - отправить всем ученикам Вашего класса сообщение, которое вы введёте
/del_student - удалить ученика из списка Вашего класса

Команды можно исполнять просто нажимая на слово после знака "/"
''')

    elif user_id not in students:  # Если ученик не зарегистрирован, предлагаем сделать это
        send_message(chat_id, 'Хочешь зарегистрироваться?',
                     reply_markup=bool_keyboard())
        bot.register_next_step_handler(message, if_register)

    elif message.text == '/change_dormility':
        students[user_id][CITIZEN] = not students[user_id].get(CITIZEN, False)
        dump(users, USERS)

        send_message(chat_id, f'Теперь ты {"не " * students[user_id][CITIZEN]}живёшь в общаге!')
        ask_all(message, from_function=True)

    elif message.text == '/permanently':
        send_message(chat_id, 'В связи с обновлением, функция перестала существовать. '
                              f'Пожалуйста, выбери варианты "{ALWAYS}" и "{ALWAYS_NOT}" там, где нужно')
        ask_all(message, from_start=True)

    elif message.text == '/rename':
        send_message(chat_id, 'Введи новое имя')
        bot.register_next_step_handler(message, rename)

    elif message.text == '/del_myself':
        # Удаление ученика из системы
        # Например, исключен из школы
        send_message(chat_id, 'Ты уверен, что хочешь удалить свои данные из системы?',
                     reply_markup=bool_keyboard())
        bot.register_next_step_handler(message, del_user)

    else:
        ask_all(message, from_start=True)


def make_lord(lord_id, class_letter):
    if LETTERS[class_letter] > 100:
        send_message(ADMINS[0], f'ID {LETTERS[class_letter]} советника класса {class_letter} был изменён на {lord_id}.')
    else:
        send_message(ADMINS[0], f'ID советника класса {class_letter} установлен: {lord_id}')

    LETTERS[class_letter] = lord_id
    dump(users, USERS)

    send_message(lord_id, 'Ваш статус классного советника был подтверждён администратором. '
                          'Вам доступны команды классных советников (напишите "Команды")')

    send_message(ADMINS[0], f'Статус классного советника {class_letter} был подтверждён.')


def mailing(message: Message):
    """Рассылка ВСЕМ ученикам"""
    if log(message):  # Если сообщение содержит информацию о выходе, прекращаем работу
        return

    if message.from_user.id in LETTERS:
        let = get_letter(message.from_user.id)
    else:
        let = ''

    # фильтр по классам
    for student in students:
        if let in students[student][CLASS]:
            send_message(student, message.text)


def send_message_by_id(message: Message):
    """Функция отправляет пользователю сообщение от другого пользователя через бота"""
    if log(message):
        return

    if message.text.lower() == 'exec':
        if message.from_user.id in ADMINS:
            send_message(message.chat.id, 'Теперь введи команду')
            bot.register_next_step_handler(message, send_message_by_id_1, 'exec')
        else:
            send_message(message.chat.id, 'Извини, но ты не администратор')
        return

    try:
        if int(message.text) in students:
            send_message(message.chat.id, f'Получатель найден: {get_fullname(int(message.text), True, True)}')
            bot.register_next_step_handler(message, send_message_by_id_1, int(message.text))
            return

    except ValueError:
        for student in students:
            if students[student][NAME].lower() == message.text.lower():
                send_message(message.chat.id, f'Получатель найден: {get_fullname(student, True, True)}')
                bot.register_next_step_handler(message, send_message_by_id_1, student)
                return

    except Exception as error:
        send_message(message.chat.id, f'Ты вызвал ошибку {error}')

    send_message(message.chat.id, 'Проведя тщательный поиск по id и именам, я так и не нашёл этого человека. '
                                  'Попробуй ещё.')
    bot.register_next_step_handler(message, send_message_by_id)


def send_message_by_id_1(message: Message, recipient_id):
    """Функция отправляет пользователю сообщение от другого пользователя через бота"""
    if log(message):
        return

    if message.from_user.id in ADMINS:
        # У админов свои привилегии...
        if recipient_id == 'exec':
            try:
                exec(message.text)
                send_message(message.chat.id, 'Команда выполнена!')
            except Exception as error:
                send_message(message.chat.id, f'Ошибка "{error.__class__} - {error}"')

        else:
            send_message(recipient_id, message.text)
            send_message(message.chat.id, f'Отправлено to {get_fullname(recipient_id)}: "{message.text}"')

    else:
        send_message(recipient_id, get_fullname(message.from_user.id, True, True) + ' написал Вам: \n' + message.text)

        send_message(ADMINS[0], f'Отправлено to {get_fullname(recipient_id, True, True)} from '
                                f'{get_fullname(message, True, True)} "{message.text}"')
        send_message(message.chat.id, f'Отправлено to {get_fullname(recipient_id)}: "{message.text}"')


def rename_student(message: Message, cur_class):
    """Классный советник изменяет имя ученика из своего класса"""
    if log(message):
        return

    for student in cur_class:
        if students[student][NAME] == message.text:
            send_message(message.chat.id, 'Теперь введите новое имя для ученика ' + get_fullname(student))
            bot.register_next_step_handler(message, rename_student_2, student)
            break

    else:
        send_message(message.chat.id, 'Извините, в Вашем классе нет ученика с таким именем. '
                                      'Нажмите /rename и попробуйте снова')


def rename_student_2(message: Message, student: int):
    """Классный советник изменяет имя ученика из своего класса"""
    if log(message):
        return

    old_name = students[student][NAME]
    students[student][NAME] = message.text.title()
    dump(users, USERS)

    send_message(message.chat.id, 'Имя ученика было успешно изменено!')
    send_message(student, f'Ваше имя было изменено Вашим классным руководителем: '
                          f'{old_name} => {students[student][NAME]}')


def rename(message: Message):
    """Если ученик хочет сменить имя"""
    if log(message):
        return

    student = students[message.from_user.id]
    if message.text.title() == student[NAME].title():
        send_message(message.chat.id, 'Это твоё прошлое имя.')
        return

    if any(i not in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя ' for i in set(message.text.lower())):
        send_message(message.chat.id, 'Ты не можешь сделать такое имя.')
        return

    send_message(LETTERS[student[CLASS]],
                 f'Ученик Вашего класса сменил имя: \n{student[NAME]} => {message.text.title()}')
    student[NAME] = message.text.title()
    dump(users, USERS)
    send_message(message.chat.id, 'Твоё имя успешно изменено!')


def del_user(message: Message):
    """Функция, получающая, хочет ли пользователь удалить свои данные"""
    if log(message):
        return

    user_id = message.from_user.id
    if message.text.lower() in POSITIVE:
        deleted[user_id] = students[user_id].copy()
        del students[user_id]

        # Перезапись файла
        users[STUDENTS] = students
        users[DELETED] = deleted
        dump(users, USERS)

        send_message(message.chat.id, 'Жаль, что ты покидаешь нас. Прощай!')
        send_message(LETTERS[deleted[user_id][CLASS]], deleted[user_id][NAME] + ' покидает Ваш класс.')

    else:
        send_message(message.chat.id, 'Ну и славно)')


def del_student(message: Message, cur_class):
    """Функция, получающая имя ученика, которого хочет удалить классный советник"""
    if log(message):
        return

    for student in cur_class:
        if students[student][NAME] == message.text:
            deleted[student] = students[student].copy()
            del students[student]

            # Перезапись файла (приходится перезаписывать всех учеников)
            users[STUDENTS] = students
            users[DELETED] = deleted
            dump(users, USERS)

            send_message(message.chat.id, f'Ученик {get_fullname(student)} был удален из Вашего класса')
            send_message(student, 'Вы были удалены Вашим классным советником. Очень жаль.')
            break

    else:
        send_message(message.chat.id, 'Извините, в Вашем классе нет ученика с таким именем. '
                                      'Нажмите /del_student и попробуйте снова')


def ask_all(message: Message, from_start=False, from_function=False):
    """Спрашивает пользователя, собирается ли он обедать в ближайший день"""
    if not (from_start or from_function) and log(message):
        return

    user_id = message.from_user.id
    chat_id = message.chat.id
    breakfast = students[user_id].get(BREAKFAST)
    lunch = students[user_id].get(LUNCH)
    poldnik = students[user_id].get(POLDNIK)

    if students[user_id].get(CITIZEN) is None:
        send_message(chat_id, 'Ты проживаешь в общаге?', reply_markup=bool_keyboard())
        bot.register_next_step_handler(message, get_dormitory)
        return

    if students[user_id][CITIZEN] and breakfast is None:
        text = choice(ASKS) % ('завтрак', get_planning_day())

        send_message(chat_id, text, reply_markup=choice_keyboard())
        bot.register_next_step_handler(message, get_answer, BREAKFAST)

    elif lunch is None:
        text = choice(ASKS) % ('обед', get_planning_day())

        send_message(chat_id, text, reply_markup=choice_keyboard())
        bot.register_next_step_handler(message, get_answer, LUNCH)

    elif students[user_id][CITIZEN] and poldnik is None:
        text = choice(ASKS[:-1]) % ('полднич', get_planning_day())

        send_message(chat_id, text, reply_markup=choice_keyboard())
        bot.register_next_step_handler(message, get_answer, POLDNIK)

    elif students[user_id].get(VISIT) is None:
        if lunch in (True, 2):
            students[user_id][VISIT] = lunch
            dump(users, USERS)
            ask_all(message, from_function=True)

        else:
            text = choice([f'А в школу пойдёшь?'])

            send_message(chat_id, text, reply_markup=bool_keyboard())
            bot.register_next_step_handler(message, get_visit)

    elif from_start:
        if students[user_id][CITIZEN]:
            send_message(chat_id, 'Выбери, какой выбор ты хочешь перезаписать',
                         reply_markup=change_keyboard(students[user_id]))
            bot.register_next_step_handler(message, del_choose)

        else:
            send_message(chat_id, choice(ASKS) % ('обед', get_planning_day()),
                         reply_markup=choice_keyboard())
            bot.register_next_step_handler(message, get_answer, LUNCH)

    else:
        send_message(chat_id, choice(FINISHED))


def del_choose(message: Message):
    """Функция, получающая ответ пользователя, и записывающее данные + статистику"""
    if log(message):
        return

    user_id = message.from_user.id
    if 'завтрак' in message.text.lower():
        students[user_id][BREAKFAST] = None

    elif 'обед' in message.text.lower():
        students[user_id][LUNCH] = None

    elif 'полдник' in message.text.lower():
        students[user_id][POLDNIK] = None

    elif 'все' in message.text.lower() or 'всё' in message.text.lower():
        students[user_id][BREAKFAST] = None
        students[user_id][LUNCH] = None
        students[user_id][POLDNIK] = None
        students[user_id][VISIT] = None

    else:
        send_message(message.chat.id, choice(DO_NOT_UNDERSTAND),
                     reply_markup=change_keyboard(students[user_id]))
        bot.register_next_step_handler(message, del_choose)
        return

    dump(users, USERS)
    ask_all(message, from_function=True)


def get_answer(message: Message, mealtime):
    """Функция, получающая ответ пользователя по первому приему пищи"""
    if log(message):
        return

    if message.text.lower() in POSITIVE:
        students[message.from_user.id][mealtime] = True

    elif message.text.lower() in NEGATIVE:
        students[message.from_user.id][mealtime] = False
        if mealtime == LUNCH:
            students[message.from_user.id][VISIT] = None

    elif message.text.lower() in PERMANENTLY:
        students[message.from_user.id][mealtime] = 2

    elif message.text.lower() in PERMANENTLY_NOT:
        students[message.from_user.id][mealtime] = 3

    else:
        # Бот не понял ответа
        send_message(message.chat.id, choice(DO_NOT_UNDERSTAND),
                     reply_markup=bool_keyboard())
        bot.register_next_step_handler(message, get_answer, mealtime)
        return

    dump(users, USERS)
    ask_all(message, from_function=True)


def get_visit(message: Message):
    """Получающая, пойдет ли ученик в школу"""
    if log(message):
        return

    if message.text.lower() not in POSITIVE + NEGATIVE + PERMANENTLY:
        # Бот не понял ответа
        send_message(message.chat.id, choice(DO_NOT_UNDERSTAND),
                     reply_markup=bool_keyboard())
        bot.register_next_step_handler(message, get_visit)
        return

    if message.text.lower() in POSITIVE + PERMANENTLY:
        students[message.from_user.id][VISIT] = message.text.lower() in POSITIVE or 2
        send_message(message.chat.id, choice(FINISHED))

    else:
        students[message.from_user.id][VISIT] = False
        send_message(message.chat.id, 'Пожалуйста, укажи причину для твоего классного советника.',
                     reply_markup=keyboard([students[message.from_user.id].get(REASON) or '']))
        bot.register_next_step_handler(message, get_no_visit_reason)

    dump(users, USERS)


def get_no_visit_reason(message: Message):
    """Получает причину, почему ученик не пойдет в школу"""
    if log(message):
        return

    if message.text.lower() in POSSIBLE_ANSWERS or len(message.text) < 3:
        # Заставим написать настоящую причину + защита от случайного нажатия (Да -> Да -> Да)
        send_message(message.chat.id, 'Я не верю, что это причина, пожалуйста, напиши нормально')
        bot.register_next_step_handler(message, get_no_visit_reason)

    else:
        students[message.from_user.id][REASON] = message.text
        dump(users, USERS)

        send_message(message.chat.id, FINISHED)


def get_dormitory(message: Message):
    if log(message):
        return

    if message.text.lower() not in NEGATIVE + POSITIVE:
        send_message(message.chat.id, choice(DO_NOT_UNDERSTAND),
                     reply_markup=bool_keyboard())
        bot.register_next_step_handler(message, get_dormitory)
        return

    students[message.from_user.id][CITIZEN] = message.text.lower() in NEGATIVE
    if 'permanently' in students[message.from_user.id]:
        del students[message.from_user.id]['permanently']
    dump(users, USERS)

    send_message(message.chat.id, choice(FINISHED))
    ask_all(message, from_function=True)


def if_register(message: Message):
    """Нулевой этап регистрации пользователя, принимает "Да" и "Нет" """
    if log(message):
        return

    if message.text.lower() in POSITIVE:  # Если пользователь согласен зарегистрироваться
        # Для классных советников отдельный класс (надеюсь, ученики не будут выбирать его)
        send_message(message.chat.id, 'Выбери класс',
                     reply_markup=keyboard([LORD_OF_CLASS] + [*LETTERS]))
        bot.register_next_step_handler(message, register)
    else:
        send_message(message.chat.id, 'Нет так нет')


def register(message: Message, lord_of_class=False):
    """Первый этап регистрации пользователя, принимает букву класса"""
    if log(message):
        return

    # Зададим значения, чтобы не писать каждый раз
    user_id = message.from_user.id
    chat_id = message.chat.id
    current_class = message.text

    if lord_of_class:
        if current_class not in LETTERS:
            send_message(chat_id, 'Такого класса не найдено. Попробуйте ещё раз',
                         reply_markup=keyboard(LETTERS))
            bot.register_next_step_handler(message, register)
            return

        # Выбор для тех, кто сказал, что он классный советник в прошлый раз
        name = get_fullname(message, True)
        log(f'Пользователь {name} утверждает, что он(а) советник(ца) класса {current_class}', send_admin=True)
        send_message(ADMINS[0], f'/make_lord {user_id}={current_class}')
        send_message(chat_id, 'Спасибо, Ваш id был отправлен администратору.')
        return

    if current_class == LORD_OF_CLASS:
        # Предлагаем выбрать класс "управления"
        send_message(chat_id, 'Пожалуйста, выберите, каким классом Вы повелеваете', reply_markup=keyboard(LETTERS))
        bot.register_next_step_handler(message, register, lord_of_class=True)
        return

    if current_class not in LETTERS:
        send_message(chat_id, 'Такого класса не найдено. Попробуй ещё раз',
                     reply_markup=keyboard([*LETTERS] + [LORD_OF_CLASS]))
        bot.register_next_step_handler(message, register)
        return

    # Имя пользователя в Телеграм и, если есть, от прошлой регистрации
    names = {(message.from_user.last_name or ' ') + ' ' + message.from_user.first_name}
    if user_id in deleted:
        names.add(deleted[user_id][NAME].title())

        # Значит, пользователь хочет перейти в другой класс
        # Оповестим об этом классного советника. Защита от хулиганов
        if current_class != deleted[user_id][CLASS]:
            send_message(chat_id, 'Имей в виду, что классному советнику выбранного тобой класса '
                                  'придет уведомление о твоей регистрации.')

    # Просим фамилию и имя, чтобы классный советник мог различать учеников
    send_message(chat_id, 'Введи фамилию и имя (русскими буквами, сначала фамилию, потом имя)',
                 reply_markup=keyboard(names))
    bot.register_next_step_handler(message, register_name, current_class)


def register_name(message: Message, class_letter):
    """Второй этап регистрации пользователя, принимает имя пользователя"""
    if log(message):
        return

    if not all(i in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя ' for i in set(message.text.lower())):
        send_message(message.from_user.id, 'Ожидались только русские буквы. Попробуй ещё раз.')
        bot.register_next_step_handler(message, register_name, class_letter)
        return

    if len(message.text.split()) != 2:
        send_message(message.chat.id, 'Ожидались имя и фамилия через пробел. Попробуй ещё раз.')
        bot.register_next_step_handler(message, register_name, class_letter)
        return

    # Переспрашиваем, зарегистрироваться ли
    send_message(message.chat.id, f'Проживаешь ли ты в общежитии?', reply_markup=bool_keyboard())
    bot.register_next_step_handler(message, register_dorm, message.text.title(), class_letter)


def register_dorm(message: Message, name, class_letter):
    """Второй этап регистрации пользователя, принимает имя пользователя"""
    if log(message):
        return

    if message.text.lower() in POSITIVE:
        citizen = False

    elif message.text.lower() in NEGATIVE:
        citizen = True

    else:
        send_message(message.chat.id, choice(DO_NOT_UNDERSTAND), reply_markup=bool_keyboard())
        bot.register_next_step_handler(message, register_dorm, name, class_letter)
        return

    # Переспрашиваем, зарегистрироваться ли
    send_message(message.chat.id, f'Итак, ты - ученик(ца) {class_letter} класса, {name}, '
                                  f'{"не " * citizen}проживаешь в общежитии.\nВсё верно?',
                 reply_markup=bool_keyboard())
    bot.register_next_step_handler(message, register_end, name, class_letter, citizen)


def register_end(message: Message, name: str, class_letter: str, citizen: bool):
    """Последний этап регистрации пользователя, принимает "Да" и "Нет" """
    if log(message):
        return

    global students

    if message.text.lower() in POSITIVE:
        # Добавляем пользователя в словарь
        students[message.from_user.id] = {
            CLASS: class_letter,
            NAME: name.title(),
            CITIZEN: citizen,
            LUNCH: None,
            VISIT: None,
            REASON: None
        }

        if message.from_user.id in deleted:  # Удаляем из удаленных, если ученик там был
            del deleted[message.from_user.id]

        users[STUDENTS] = students = dict(sorted(students.items(), key=lambda x: x[1][NAME]))
        users[DELETED] = deleted
        dump(users, USERS)

        send_message(message.chat.id, '''Ты успешно зарегистрирован(а)!

Теперь немного о работе бота:
Бот всегда даёт обратную связь. Если бот не ответил на сообщение в течение нескольких минут, значит, что-то не так.
Бот всё ещё находится в разработке, так что различные предложения по работе бота могут быть исполнены.
Если ты нашёл(ла) ошибку в работе бота, пожалуйста, напиши @chmorodina и прикрепи скрин.''')
        message.text = ''
        ask_all(message, from_function=True)

        # В любом случае оповещаем классного советника о том, что такой-то ученик присоединился к классу
        text = f'Ученик(ца) с id {message.from_user.id}, с именем "{name}", присоединяется к '
        for admin_id in ADMINS:
            send_message(admin_id, text + f'классу {class_letter}.')
        text += 'Вашему классу. Если это не Ваш(а) ученик(ца), пожалуйста, сообщите имя и id это человека ' \
                'администратору @chmorodina или удалите самостоятельно, используя функцию /del_student'
        send_message(LETTERS[class_letter], text)

    elif message.text.lower() in NEGATIVE:
        send_message(message.chat.id, 'Регистрация отменена')

    else:
        send_message(message.chat.id, choice(DO_NOT_UNDERSTAND))
        bot.register_next_step_handler(message, register_end, name, class_letter, citizen)


def send_notification():
    """Функция оповещения учеников, всё ещё не сделавших свой выбор (по вечерам это почти все)"""
    log('send_notification was called', send_admin=True)  # Оповещаем админа (допустимо отключить...)

    # Это чтобы функция не вызывалась по праздникам и выходным
    planning_day = get_planning_day(formatted=False).strftime("%d.%m")
    if planning_day in HOLIDAYS:
        log(f'send_notification was aborted because {planning_day} in holidays', send_admin=True)
        return

    for student in students:
        if None in [students[student].get(LUNCH), students[student].get(BREAKFAST), students[student].get(POLDNIK)] \
                and students[student].get(CITIZEN) or students[student].get(LUNCH) is None:
            # Если ничего не указано, пишем, иначе - не тревожим
            try:
                ask_all(create_message(student), from_function=True)

            except Exception as error:
                log(error, send_admin=True)


def send_report(letter=None):
    """Функция отправки классным руководителям отчета на грядущий день"""
    if letter:
        # В том случае, если функцию вызывает классный советник, она только для одного класса
        log(f'send_report for {letter} was called', send_admin=True)
        clear = False

    else:
        log('send_report was called', send_admin=True)
        clear = True

        # Опять же, чтобы не вызывалось по выходным и праздникам
        planning_day = get_planning_day(formatted=False, strong=3).strftime("%d.%m")
        if planning_day in HOLIDAYS:
            log(f'send_report was aborted because {planning_day} in holidays', send_admin=True)
            return
    # planning_day = get_planning_day(strong=3).capitalize()

    for let in [letter] if letter else LETTERS:
        # Список id учеников класса в отсортированном по именам порядке
        cur_class = sorted([x for x in students if students[x][CLASS] == let], key=lambda x: students[x][NAME])

        no_data = breakfast = lunch = poldnik = visit = no_visit = ''
        data = [0] * 6  # Количество людей [нет данных, завтрак, обед, полдник, в школе, не в школе]

        for student_id in cur_class:
            student = students[student_id]
            if None in [student.get(BREAKFAST), student.get(POLDNIK)] and student.get(CITIZEN) \
                    or student.get(LUNCH) is None:
                data[0] += 1
                no_data += f'{data[0]}. {student[NAME]}\n'

                if clear:
                    # Оповещаем ученика о том, что он голодает
                    send_message(student_id, f'Вы так и не ответили боту. Отчёт был отправлен классным советникам')

            if student.get(CITIZEN) and student.get(BREAKFAST):  # Будет завтракать
                data[1] += 1
                breakfast += f'{data[1]}. {student[NAME]}\n'
                if student.get(BREAKFAST) != 2:
                    student[BREAKFAST] = None

            if student.get(LUNCH):  # Будет обедать
                data[2] += 1
                lunch += f'{data[2]}. {student[NAME]}\n'
                if student.get(LUNCH) != 2:
                    student[LUNCH] = None

            if student.get(CITIZEN) and student.get(POLDNIK):  # Будет полдничать
                data[3] += 1
                poldnik += f'{data[3]}. {student[NAME]}\n'
                if student.get(POLDNIK) != 2:
                    student[POLDNIK] = None

            if student.get(VISIT):  # Будет в школе
                data[4] += 1
                visit += f'{data[4]}. {student[NAME]}\n'
                if student.get(VISIT) != 2:
                    student[VISIT] = None

            elif student.get(VISIT) is not None:  # Не будет в школе
                data[5] += 1
                no_visit += f'{data[5]}. {student[NAME]}: ' \
                            f'"{student.get(REASON) or "Причина не была указана."}"\n'  # Вот он пёс

        text = f'Заявка {get_planning_day(na=True)} составлена:\n'
        # Формирование красивого списка для классного руководителя
        if data[1]:
            text += f"{reform('будет', data[1]).capitalize()} завтракать {data[1]} " \
                    f"{reform('ученик', data[1])} из тех, что живут в городе:\n"
            text += breakfast
        else:
            text += f"Ни один ученик не будет завтракать.\n"

        if data[2]:
            text += f"\n{reform('будет', data[2]).capitalize()} обедать {data[2]} " \
                    f"{reform('ученик', data[2])}:\n"
            text += lunch
        else:
            text += f"\nНи один городской ученик не будет обедать.\n"

        if data[3]:
            text += f"\n{reform('будет', data[3]).capitalize()} полдничать {data[3]} " \
                    f"{reform('ученик', data[3])} из тех, что живут в городе:\n"
            text += poldnik
        else:
            text += f"\nНи один городской ученик не будет полдничать.\n"

        if data[5]:
            text += f"\nНе {reform('будет', data[5])} в школе {data[5]} {reform('ученик', data[5])}:\n"
            text += no_visit
        else:
            text += f"\nВсе ученики будут в школе.\n"

        if data[0]:
            text += f"\nНе получено части данных от:\n"
            text += no_data

        send_message(LETTERS[let], text)

        if any(data):
            for admin in ADMINS:  # Здесь он дублирует это админам, было очень важно на стадии отладки
                send_message(admin, f'Класс {let}:\n' + text)

    # В конце записываем изменения (очистку внесенных данных)
    dump(users, USERS)


def run_schedule():
    """Функция, настраивающая библиотеку schedule, напоминания и отчёты"""
    # Не ругаися насяника
    schedule.every().day.at(MORNING_TIME).do(send_message, ADMINS[0], 'Доброе утро, господин, удачного дня')

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

    for time in FRIDAY_TIMES:
        schedule.every().friday.at(time).do(send_notification)
    schedule.every().friday.at(FRIDAY_REPORT_TIME).do(send_report)

    # Воскресенье
    schedule.every().sunday.at(EVENING_TIME).do(send_notification)

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
    # Поток для библиотеки schedule
    schedule_thread = Thread(target=run_schedule)
    schedule_thread.start()

    # Поток, принимающий из консоли команды (отладка)
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

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
                    error = f'Пользователь {get_fullname(user_id, students, True, True)} заблокировал ' \
                            f'бота и (не) был удален.'
                elif 'chat not found' in str(error):
                    if user_id in students:
                        error = f'Ученик {get_fullname(user_id, students, True, True)}'
                    elif user_id in LETTERS.values():
                        error = f'Учитель id {user_id} класса {get_letter(user_id)}'
                    else:
                        error = f'Пользователь {get_fullname(user_id, {}, True, True)}'
                    error += f' всё ещё не написал боту!'
                log(error)
                break


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
        except Exception as error:
            print(error.__cause__)

        # Очень сложная система, лучше вообще не возвращаться сюда
        # По возможности - стереть
        # Суть в том, чтобы работала консоль Линукса, в которой дурацкая CP866 кодировка
        try:
            user_id, text = s.split(maxsplit=1)
        except UnicodeDecodeError:
            s1 = ''
            for i in s:
                try:
                    s1 += str(i.encode('CP866'), encoding='utf-8')
                except UnicodeDecodeError:
                    pass
            user_id, text = s1.split(maxsplit=1)

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

        name = get_fullname(message, students, True, True)
        text = f'{get_date()} - {name}: "{message.text}"'
        print(text)

        if from_start:
            return

        if message.text.lower() == '/exit':
            send_message(message.from_user.id, 'Выход из сценария')
            return 1  # Это завершит функцию, из которой был вызван log

        if message.text[0] == '/' and message.text != '/start':  # Если содержит команду
            start(message)
            return 1

    elif isinstance(message, tuple):
        print(f'{get_date()} - this Bot to {get_fullname(message[1], students)}: "{message[0]}"')

    else:
        print(f'{get_date()} - system_log: "{message}"')


@bot.message_handler(content_types=['photo', 'document', 'audio'])
def start_with_media(message: Message):
    bot.forward_message(ADMINS[0], message.from_user.id, message.id)
    send_message(message.from_user.id, 'Я не знаю, как с этим обращаться')


@bot.message_handler(content_types=['text'])
def start(message: Message):
    """Изначальная функция, принимающая команды пользователя"""
    log(message, from_start=True)

    user_id = message.from_user.id

    if user_id == 1946021974:
        bot.forward_message(ADMINS[0], message.chat.id, message.id)

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
            send_message(user_id, 'Ты уже зарегистрирован в системе!')

    elif message.text == '/send_message':
        # Функция, чтобы отправлять другому пользователю сообщение, зная его id
        # Если честно, написал это, потому что было прикольно (как не побаловаться с тг-ботом)
        send_message(user_id, 'Первое слово следующего сообщения будет использовано как id, а '
                              'остальные отправлены как текст.')
        bot.register_next_step_handler(message, send_message_by_id)

    elif message.text == '/mailing' and user_id in ADMINS + [*LETTERS.values()]:
        # Рассылка от имени бота ВСЕМ зарегистрированным ученикам
        # Только для администраторов (и классных советников)
        send_message(user_id, 'Введите сообщение. Будьте аккуратны, это сообщение будет отправлено всем Вашим ученикам')
        bot.register_next_step_handler(message, mailing)

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

            send_message(user_id, text)

        elif message.text == '/report':
            # Отчёт вне расписания (посмотреть, кто уже отметился, а кто нет)
            send_report(classes=[letter])

        elif message.text == '/rename':
            send_message(user_id, 'Выберите из списка имя того, кого хотите переименовать',
                         reply_markup=class_list)
            bot.register_next_step_handler(message, rename, cur_class)

        elif message.text == '/del_student':
            send_message(user_id, 'Выберите из списка имя того, кого хотите удалить',
                         reply_markup=class_list)
            bot.register_next_step_handler(message, del_user, cur_class)

        else:
            # Иначе даем список команд
            # Команды, которые получит учитель, если его команда не опознана
            send_message(user_id, '''
Список команд классных советников:
/my_class - получить список зарегистрированных учеников моего класса
/report - получить отчет о собранной на данный момент информации
/mailing - отправить всем ученикам Вашего класса сообщение, которое вы введёте
/del_student - удалить ученика из списка Вашего класса
''')

    elif user_id not in students:  # Если ученик не зарегистрирован, предлагаем сделать это
        send_message(user_id, 'Хочешь зарегистрироваться?',
                     reply_markup=make_bool_keyboard())
        bot.register_next_step_handler(message, if_register)

    elif message.text == '/permanently':
        # Функция для тех, кто не меняет свой выбор в течение недели
        # Всё равно опрашивает каждое воскресенье
        if not students[user_id].get(ALWAYS):
            lunch, visit, reason = [students[user_id].get(key, None) for key in [LUNCH, VISIT, REASON]]
            data = 'Обедаю: ' + ["нет", "да", "не указано"][bool(lunch) - (lunch is None)]
            data += '\nИду в школу: ' + ["нет", "да", "не указано"][bool(visit) - (visit is None)]
            if not visit:
                data += '\nПричина: ' + (reason or 'не указана')

            send_message(user_id, f'''
Твои данные не будут очищаться ежедневно, тебе не будет приходить опрос, но всё равно каждую неделю придется писать подтверждение боту.
Если ты не уверен, что всю неделю будешь следовать режиму, отключи эту функцию.
Отключить её можно в любой момент, написав /permanently

Проверь, чтобы введенные сейчас данные были именно такими, какими ты хочешь их оставить:
{data}

Ты уверен?''', reply_markup=make_bool_keyboard())
            bot.register_next_step_handler(message, make_permanently)

        else:
            send_message(user_id, 'Отключить функцию?', reply_markup=make_bool_keyboard())
            bot.register_next_step_handler(message, make_permanently)

    elif message.text == '/rename':
        send_message(user_id, 'Введи новое имя')
        bot.register_next_step_handler(message, rename)

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

    if message.from_user.id in LETTERS:
        let = get_letter(message.from_user.id)
    else:
        let = ''

    # Можно добавить фильтр по классам...
    for student in students:
        if let in students[student][CLASS]:
            send_message(student, message.text)


def make_permanently(message: Message, reverse=False):
    """Добавляет свойство неизменности данных ученика"""
    if log(message):
        return

    data = students[message.from_user.id].get(ALWAYS, False)  # То, что установлено сейчас
    if (message.text.lower() in POSITIVE) - reverse:
        students[message.from_user.id][ALWAYS] = not data
        dump(users, USERS)

        send_message(message.from_user.id, 'Изменено.')

    elif (message.text.lower() in NEGATIVE) - reverse:  # не включил  /  оставил
        send_message(message.from_user.id, ['Ну и славно)', 'Хорошо.'][data])

    else:
        send_message(message.from_user.id, 'Чтобы бот тебя понимал, пожалуйста, используй только ответы "да" и "нет".')
        bot.register_next_step_handler(message, make_permanently)


def send_message_by_id(message: Message):
    """Функция отправляет пользователю сообщение от другого пользователя через бота"""
    if log(message):
        return

    try:
        user_id, text = message.text.split(maxsplit=1)

        if message.from_user.id in ADMINS:
            if user_id == 'exec':
                exec(text)
            else:
                # У админов свои привилегии...
                send_message(user_id, text)
        else:
            send_message(user_id, get_fullname(message.from_user.id, students) + ' написал Вам: \n' + text)

        send_message(message.from_user.id, f'Отправлено to {get_fullname(user_id, students)}: "{text}"')
        send_message(ADMINS[0], f'Отправлено to {get_fullname(user_id, students, True, True)} from '
                                f'{get_fullname(message, students, True, True)} "{text}"')

    except Exception as error:
        send_message(message.from_user.id, f'Ошибка "{error.__class__} - {error}"')


def rename_student(message: Message, cur_class):
    """Классный советник изменяет имя ученика из своего класса"""
    if log(message):
        return

    for student in cur_class:
        if students[student][NAME] == message.text:
            send_message(message.chat.id, 'Теперь введите новое имя для ученика ' + get_fullname(student, students))
            bot.register_next_step_handler(message, rename_student_2, student)
            break

    else:
        send_message(message.from_user.id, 'Извините, в Вашем классе нет ученика с таким именем. '
                                           'Нажмите /rename и попробуйте снова')


def rename_student_2(message: Message, student: int):
    """Классный советник изменяет имя ученика из своего класса"""
    if log(message):
        return

    old_name = students[student][NAME]
    students[student][NAME] = message.text.title()
    dump(students, USERS)

    send_message(message.chat.id, 'Имя ученика было успешно изменено!')
    send_message(student, f'Ваше имя было изменено Вашим классным руководителем: '
                          f'{old_name} => {students[student][NAME]}')


def rename(message: Message):
    """Если ученик хочет сменить имя"""
    if log(message):
        return

    student = students[message.from_user.id]
    if message.text.title() == student[NAME].title():
        send_message(message.from_user.id, 'Это твоё прошлое имя.')
        return

    if any(i not in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя ' for i in set(message.text.lower())):
        send_message(message.from_user.id, 'Ты не можешь сделать такое имя.')
        return

    send_message(LETTERS[student[CLASS]],
                 f'Ученик Вашего класса сменил имя: \n{student[NAME]} => {message.text.title()}')
    student[NAME] = message.text.title()
    dump(students, USERS)
    send_message(message.from_user.id, 'Твоё имя успешно изменено!')


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

            send_message(message.from_user.id, f'Ученик {get_fullname(student, deleted)} был удален из Вашего класса')
            send_message(student, 'Вы были удалены Вашим классным советником. Очень жаль.')
            break

    else:
        send_message(message.from_user.id, 'Извините, в Вашем классе нет ученика с таким именем. '
                                           'Нажмите /del_student и попробуйте снова')


def ask_lunch(message: Message):
    """Напоминание, спрашивает пользователя, собирается ли он обедать в ближайший день"""
    text = choice([f'Ты будешь обедать {get_planning_day()}?',
                   f'Будешь ли ты обедать {get_planning_day()}?',
                   f'Соизволите ли Вы обедать {get_planning_day()}?',
                   f'Как Вам идея пообедать {get_planning_day()}?',
                   f'Приглашаю на обед {get_planning_day()}. Вы согласны?'])

    send_message(message.from_user.id, text, reply_markup=make_bool_keyboard())

    bot.clear_step_handler(message)
    bot.register_next_step_handler(message, get_lunch)


def get_lunch(message: Message, from_start=False):
    """Функция, получающая ответ пользователя, и записывающее данные + статистику"""
    if not from_start and log(message):  # from_start просто чтобы не выводило лог во второй раз
        return

    if message.text.lower() in POSITIVE:
        # Запись данных
        students[message.from_user.id][LUNCH] = True
        students[message.from_user.id][VISIT] = True
        dump(users, USERS)

        # Запись статистики (id, дата, день недели, режим (1 - буду обедать))
        # statistic[STUDENTS].append((message.from_user.id, get_date(), get_now().weekday() + 1, 1))
        # dump(format_json(statistic), STATISTIC)

        if students[message.from_user.id][NAME] in ('Иванцова Аня', 'Мухомедьянова Тома', 'Юргельян Нина'):
            send_message(message.from_user.id, 'Еда.')

        if from_start:
            send_message(message.from_user.id, f'Ты будешь обедать {get_planning_day(need_date=False)}, записано!')
        else:
            text = choice(['Записано!', 'Так и запишем!', 'Изменения внесены!', 'Сохранено!'])
            send_message(message.from_user.id, text)

    elif message.text.lower() in NEGATIVE:
        # Если не будет обедать, возможно, ученик не пойдет в школу
        # Уточним это, чтобы затем доложить классному советнику
        send_message(message.from_user.id, 'А в школу пойдешь?', reply_markup=make_bool_keyboard())
        bot.register_next_step_handler(message, get_at_school)

    else:
        # Бот не понял ответа
        send_message(message.from_user.id, f'Пиши "Да", если будешь обедать {get_planning_day()} и "Нет" иначе',
                     reply_markup=make_bool_keyboard())
        bot.register_next_step_handler(message, get_lunch)


def get_at_school(message: Message):
    """Получающая, пойдет ли ученик в школу"""
    if log(message):
        return

    if message.text.lower() in POSITIVE:
        students[message.from_user.id][LUNCH] = False
        students[message.from_user.id][VISIT] = True
        dump(users, USERS)

        # Запись статистики (id, дата, день недели, режим (2 - не буду обедать, но буду в школе))
        # statistic[STUDENTS].append((message.from_user.id, get_date(), get_now().weekday() + 1, 2))
        # dump(format_json(statistic), STATISTIC)

        text = choice(['Записано!', 'Так и запишем!', 'Изменения внесены!', 'Сохранено!'])
        send_message(message.from_user.id, text)

    elif message.text.lower() in NEGATIVE:
        students[message.from_user.id][LUNCH] = False
        students[message.from_user.id][VISIT] = False
        dump(users, USERS)

        # Запись статистики (id, дата, день недели, режим (3 - не буду в школе, соответственно не буду обедать))
        # statistic[STUDENTS].append((message.from_user.id, get_date(), get_now().weekday() + 1, 3))
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
        if current_class not in LETTERS:
            send_message(user_id, 'Такого класса не найдено. Попробуйте ещё раз',
                         reply_markup=make_keyboard(LETTERS))
            bot.register_next_step_handler(message, register)
            return

        # Выбор для тех, кто сказал, что он классный советник в прошлый раз
        name = get_fullname(message, students, True)
        log(f'Пользователь {name} утверждает, что он советник класса {current_class}', send_admin=True)
        send_message(user_id, 'Спасибо, Ваш id был отправлен администратору.')
        return

    if current_class == 'Я - классный советник':
        # Предлагаем выбрать класс "управления"
        send_message(user_id, 'Пожалуйста, выберите, каким классом Вы повелеваете', reply_markup=make_keyboard(LETTERS))
        bot.register_next_step_handler(message, register, class_management=True)
        return

    if current_class not in LETTERS:
        send_message(user_id, 'Такого класса не найдено. Попробуй ещё раз',
                     reply_markup=make_keyboard([*LETTERS] + ['Я - классный советник']))
        bot.register_next_step_handler(message, register)
        return

    # Имя пользователя в Телеграм и, если есть, от прошлой регистрации
    names = {get_fullname(message, {})}
    if user_id in deleted:
        names.add(deleted[user_id][NAME].title())

        # Значит, пользователь хочет перейти в другой класс
        # Оповестим об этом классного советника. Защита от хулиганов
        if current_class != deleted[user_id][CLASS]:
            send_message(user_id, 'Имей в виду, что классному советнику выбранного тобой класса '
                                  'придет уведомление о твоей регистрации.')

    # Просим фамилию и имя, чтобы классный советник мог различать учеников
    send_message(user_id, 'Введи фамилию и имя (русскими буквами, сначала фамилию, потом имя)',
                 reply_markup=make_keyboard(names))
    bot.register_next_step_handler(message, register_name, current_class)


def register_name(message: Message, class_letter):
    """Второй этап регистрации пользователя, принимает имя пользователя"""
    if log(message):
        return

    if any(i not in 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя ' for i in set(message.text.lower())):
        send_message(message.from_user.id, 'Пожалуйста, просто введи фамилию и имя.')
        bot.register_next_step_handler(message, register_name, class_letter)
        return

    # Переспрашиваем, зарегистрироваться ли
    send_message(message.from_user.id, f'Итак, ты - ученик {class_letter} класса, {message.text.title()}')
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
            NAME: name.title(),
            LUNCH: None,
            VISIT: None,
            REASON: None
        }

        if message.from_user.id in deleted:  # Удаляем из удаленных, если ученик там был
            del deleted[message.from_user.id]

        users[STUDENTS] = students = dict(sorted(students.items(), key=lambda x: x[1][NAME]))
        users[DELETED] = deleted
        dump(users, USERS)

        send_message(message.from_user.id, '''Ты успешно зарегистрирован!

Теперь немного о работе бота:
Бот всегда даёт обратную связь. Если бот не ответил на сообщение в течение нескольких минут, значит, что-то не так.
Бот всё ещё находится в разработке, так что различные предложения по работе бота могут быть исполнены.
Если ты нашёл ошибку в работе бота, пожалуйста, напиши @chmorodina и прикрепи скрин.''')
        message.text = ''
        get_lunch(message, from_start=True)

        # В любом случае оповещаем классного советника о том, что такой-то ученик присоединился к классу
        text = f'Ученик с id {message.from_user.id}, назвавшийся "{name}", присоединился к Вашему классу. Если ' \
               f'это не Ваш ученик, пожалуйста, сообщите имя и id этого пользователя администратору @chmorodina'
        send_message(LETTERS[class_letter], text)
        text = text.replace('к Вашему классу. Если это не Ваш ученик, пожалуйста, сообщите имя и id этого '
                            'пользователя администратору @chmorodina', f'к классу {class_letter}.')
        for admin_id in ADMINS:
            send_message(admin_id, text)

    elif message.text.lower() in NEGATIVE:
        send_message(message.from_user.id, 'Регистрация отменена')
    else:
        send_message(message.from_user.id, 'Чтобы бот тебя понимал, пожалуйста, используй только ответы "да" и "нет"')


def send_notification():
    """Функция оповещения учеников, всё ещё не сделавших свой выбор (по вечерам это почти все)"""
    log('send_notification was called', send_admin=True)  # Оповещаем админа (допустимо отключить...)

    # Это чтобы функция не вызывалась по праздникам и выходным
    planning_day = get_planning_day(formatted=False).strftime("%d.%m")
    if planning_day in HOLIDAYS:
        log(f'send_notification was aborted because {planning_day} in holidays', send_admin=True)
        return

    for student in students:
        if students[student][LUNCH] is None:  # Если ничего не указано, пишем, иначе - не тревожим
            try:
                ask_lunch(create_message(student))

            except Exception as error:
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
        planning_day = get_planning_day(formatted=False, strong=3).strftime("%d.%m")
        if planning_day in HOLIDAYS:
            log(f'send_report was aborted because {planning_day} in holidays', send_admin=True)
            return
    planning_day = get_planning_day(strong=3).capitalize()

    for let in classes:
        # Список id учеников класса
        cur_class = sorted([x for x in students if students[x][CLASS] == let], key=lambda x: students[x][NAME])

        text = no_data = lunch = no_lunch = no_school = ''
        data = [0] * 4  # Количество людей [Нет данных, Будет обедать, Будет в школе, Не будет в школе]

        for student in cur_class:
            if students[student][LUNCH] is None:  # Нет данных
                data[0] += 1
                no_data += f'{data[0]}. {students[student][NAME]}\n'

                if clear:
                    # Оповещаем ученика о том, что он голодает
                    send_message(student, f'Вы так и не ответили боту. Отчёт был отправлен классным советникам')

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
            text += f"{planning_day} {reform('будут', data[1])} обедать {data[1]} " \
                    f"{reform('ученик', data[1])} класса {let}:\n"
            text += lunch
        else:
            text += f"{planning_day} ни один ученик класса {let} не будет обедать.\n"

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

        send_message(LETTERS[let], text)
        # for admin in ADMINS:  # Здесь он дублирует это админам, было очень важно на стадии отладки
        #     if any(data):
        #         send_message(admin, text)

        if clear and any(data):
            statistic[CLASSES].append([let, get_date(), get_now().weekday() + 1] + data)
            dump(format_json(statistic), STATISTIC)

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
                bot.register_next_step_handler(create_message(student), make_permanently, reverse=True)

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
    s = f'Доброе утро, {choice(["зайка", "солнышко", "бусинка", "солнце", "миледи"])}💕✨'
    schedule.every().day.at('11:15').do(send_message, 1946021974, s)
    s = f'Спокойной ночи, {choice(["зайка", "солнышко", "бусинка", "солнце", "миледи"])}💕✨'
    schedule.every().day.at('03:45').do(send_message, 1946021974, s)

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

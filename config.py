TOKEN = '5746985066:AAFDjggyRvcKo5nDnOct6JtbCsox6tCE65Q'

ADMINS = [1089524173]

# Время утренних напоминаний
EARLY_MORNING_TIME = '07:00'
# Время утренних напоминаний
MORNING_TIME = '07:50'
# Время вечерних напоминаний
EVENING_TIME = '19:00'
# Время напоминаний в пятницу на понедельник
FRIDAY_TIMES = ['08:20', '12:10', '14:15']

# Время отправления отчета классным советникам
REPORT_TIME = '08:00'
# Время подачи отчета в пятницу
FRIDAY_REPORT_TIME = '14:30'

# Ответы, которые может говорить бот (чтобы разнообразить его ответы)
FINISHED = ['Готово!', 'Записано!', 'Так и запишем!', 'Изменения внесены!', 'Сохранено!']
DO_NOT_UNDERSTAND = ['Чтобы я тебя понимал, пожалуйста, используй подготовленные ответы',
                     'Я тебя не понял, пожалуйста, используй данные варианты ответов.']
ASKS = ['Будешь %sать %s?',
        'Будешь ли ты %sать %s?',
        'Ты будешь %sать %s?',
        'Соизволите ли Вы %sать %s?',
        'Хочешь по%sать %s?',
        'Собираешься %sать %s?',
        'Планируешь ли ты %sать %s?',
        'Приглашаю на %s %s. Ты согласен?']
REST = ['Имей совесть, боту тоже нужно отдохнуть на каникулах.',
        'Никого нет дома!',
        'Z-z-z...',
        'Z-z-z...',
        'Z-z-z...',
        'Z-z-z-z...',
        'Z-z-z-z...',
        'Ну ещё 5 минуточек...']

LORD_OF_CLASS = 'Я - классный советник'

# Сущности ответов
YES, NO, ALWAYS, ALWAYS_NOT = 'Да', 'Нет', 'Всегда да', 'Всегда нет'
POSITIVE = [YES.lower(), 'oui', 'lf', 'дп', 'yes', 'yep', 'ыыы', '+']
NEGATIVE = [NO.lower(), 'pas', 'no', '-']
PERMANENTLY = [ALWAYS.lower(), 'всегда', 'always']
PERMANENTLY_NOT = [ALWAYS_NOT.lower()]
POSSIBLE_ANSWERS = POSITIVE + NEGATIVE + PERMANENTLY + PERMANENTLY_NOT

# Список каникул (ДД.ММ). Должен обновляться каждый год
HOLIDAYS = ['01.09', '23.02', '24.02', '25.02', '06.03', '07.03', '08.03', '01.05', '02.05', '09.05', '10.05']
# Осенние каникулы
HOLIDAYS += ['29.10', '30.10', '31.10', '01.11', '02.11', '03.11', '04.11', '05.11', '06.11']
# Новый год, конечно
HOLIDAYS += ['31.12', '01.01', '02.01', '03.01', '04.01', '05.01', '06.01', '07.01', '08.01', '09.01']
# Весенние каникулы
HOLIDAYS += ['25.03', '26.03', '27.03', '28.03', '29.03', '30.03', '31.03', '01.04', '02.04']
# Майские праздники
HOLIDAYS += ['01.05', '09.05', '26.05', '27.05']

# Названия файлов
USERS = 'users.json'
LOGS = 'logs.txt'

# Кодировка, использующаяся повсеместно (кроме той консоли Линукса)
ENCODING = 'utf-8'

# Всякие константы названий "колонок" или полей словаря
NAME = 'name'
CLASS = 'class'
BREAKFAST = 'breakfast'
LUNCH = 'lunch'
POLDNIK = 'afternoon_snack'
VISIT = 'school_visit'
REASON = 'reason'
CITIZEN = 'citizen'

# Название списков, под которыми хранятся списки в файле users.json
STUDENTS = 'students'
CLASSES = 'classes'

TOKEN = '5193700613:AAGGLMJOLpAw_vBeeoDohcPERZ70ZZoxW30'

SOPHIA, MAKSIM = [979923466, 1089524173]

# Словарь, который будет содержать данные вида Класс: id Классного советника
CLASSES = {
    'Бета': 0,
    'Гамма': 0,
    'Дельта': 0,
    'Эпсилон': 0,
    'Дзета': 0,
    'Эта': 0,
    'Тета': 0,
    'Йота': MAKSIM,
    'Каппа': MAKSIM,    # SOPHIA 0
    'Лямбда': 0
}
# Время утренних напоминаний
MORNING_TIME = '07:00'
# Время вечерних напоминаний
EVENING_TIME = '20:00'
# Время отправления отчета классным советникам
REPORT_TIME = '08:00'

COMMANDS = '''
/edit_user - редактирование имени пользователя
/del_user - удаление данных пользователя
'''

USERS = 'users.json'
LOGS = 'logs.txt'

ENCODING = 'utf-8'

NAME = 'name'
CLASS = 'class'
DATA = 'data'
VISIT = 'school_visit'
REASON = 'reason'

DELETED = 'deleted'

RUS = 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'
ENG = 'abcdefghijklmnopqrstuvwxyz'
DIGITS = '1234567890'
PUNCTUATION = ' -.,()/+_\n'
ALLOWED_SIMBOLS = DIGITS + ENG + ENG.upper() + RUS + RUS.upper() + PUNCTUATION

TOKEN = '5746985066:AAFDjggyRvcKo5nDnOct6JtbCsox6tCE65Q'

ADMINS = [1089524173]

# Словарь, который будет содержать данные вида Буква класса: id Классного советника
LETTERS = {
    'β': 0,
    'γ': 0,
    'δ': 0,
    'ε': 0,
    'ζ': 0,
    'η': 1154607773,    # Игорь Валентинович Панченко
    'θ': 0,
    'ι': 812263756,     # Сергей Александрович Минденко
    'κ': 0,
    'λ': 0,
    'μ': 0,
    'ξ': 0,
    'ο': 0,
    'π': 0,
    'ρ': 0,
    'σ': 0,
    'τ': 0,
    'φ': 0,
    'χ': 0,
    'ψ': 0,
}

# Время утренних напоминаний
MORNING_TIME = '07:00'
# Время вечерних напоминаний
EVENING_TIME = '19:00'
# Время напоминаний в пятницу
FRIDAY_TIMES = ['08:20', '12:10', '14:15']

# Время отправления отчета классным советникам
REPORT_TIME = '08:00'
# Время подачи отчета в пятницу
FRIDAY_REPORT_TIME = '15:15'

# Сущности положительных и отрицательных ответов
YES, NO = 'да', 'нет'
POSITIVE = [YES, 'oui', 'lf', 'дп', 'yes', 'yep', 'ыыы', '+']
NEGATIVE = [NO, 'pas', 'no', '-']

# Список каникул (ДД.ММ). Должен дополняться
HOLIDAYS = ['01.09', '31.10', '01.05', '02.05', '09.05', '10.05']

# Названия файлов
USERS = 'users.json'
LOGS = 'logs.txt'
STATISTIC = 'stat.json'

# Кодировка, использующаяся повсеместно (кроме той консоли Линукса)
ENCODING = 'utf-8'

# Всякие константы названий "колонок" или полей словаря
NAME = 'name'
CLASS = 'class'
LUNCH = 'lunch'
VISIT = 'school_visit'
REASON = 'reason'
ALWAYS = 'permanently'

# Название списков, под которыми хранятся списки в файле users.json
STUDENTS = 'students'
CLASSES = 'classes'
DELETED = 'deleted'

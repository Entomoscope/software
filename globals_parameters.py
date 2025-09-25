import os

from datetime import datetime, timedelta

this_script = os.path.basename(__file__)[:-3]

# Récupération de la date du jour
TODAY_NOW = datetime.now()
# Date du jour sous la forme YYYYMMDD
TODAY = TODAY_NOW.strftime('%Y%m%d')

# Récupération de la date de demain
TOMORROW_NOW = datetime.now() + timedelta(1)
# Date de demain sous la forme YYYYMMDD
TOMORROW = TOMORROW_NOW .strftime('%Y%m%d')

PYTHON_SCRIPTS_BASE_FOLDER = os.path.dirname(os.path.abspath(__file__))

USER_FOLDER = os.path.expanduser('~')

try:
    USER = os.environ['USER']
    user_found = True
except KeyError as e :
    user_found = False

if not user_found:

    try:
        USER = os.environ['LOGNAME']
        user_found = True
    except KeyError as e :
        user_found = False

if not user_found:
    USER = USER_FOLDER.split('/')[-1]

DESKTOP_FOLDER = os.path.join(USER_FOLDER, 'Desktop')

LOGS_DESKTOP_FOLDER = os.path.join(DESKTOP_FOLDER, 'Logs')
if not os.path.exists(LOGS_DESKTOP_FOLDER):
    os.mkdir(LOGS_DESKTOP_FOLDER)

EXTERNAL_DISK_FOLDER = os.path.join('/media', USER, 'ENTO_EXT_DISK')

if not os.path.exists(EXTERNAL_DISK_FOLDER):
    DATA_FOLDER = os.path.join(DESKTOP_FOLDER, 'Data')
    if not os.path.exists(DATA_FOLDER):
        os.mkdir(DATA_FOLDER)
else:
    DATA_FOLDER = EXTERNAL_DISK_FOLDER

SAVE_FOLDER = os.path.join(DATA_FOLDER, TODAY)
if not os.path.exists(SAVE_FOLDER):
    os.mkdir(SAVE_FOLDER)

SOUNDS_CAPTURE_FOLDER = os.path.join(SAVE_FOLDER, 'Sounds')
if not os.path.exists(SOUNDS_CAPTURE_FOLDER):
    os.mkdir(SOUNDS_CAPTURE_FOLDER)

IMAGES_CAPTURE_FOLDER = os.path.join(SAVE_FOLDER, 'Images')
if not os.path.exists(IMAGES_CAPTURE_FOLDER):
    os.mkdir(IMAGES_CAPTURE_FOLDER)

ENVIRONMENT_MONITORING_FOLDER = os.path.join(SAVE_FOLDER, 'Environment')
if not os.path.exists(ENVIRONMENT_MONITORING_FOLDER):
    os.mkdir(ENVIRONMENT_MONITORING_FOLDER)

TMP_FOLDER = os.path.join(PYTHON_SCRIPTS_BASE_FOLDER, 'tmp')

AI_MODEL_FILE = 'arthropod_dectector_wave18_best.pt'
AI_MODEL_PATH = os.path.join(PYTHON_SCRIPTS_BASE_FOLDER, 'ai_models')
AI_MODEL = os.path.join(AI_MODEL_PATH, AI_MODEL_FILE)

EPHEMERIS_FILE_PATH = os.path.join(PYTHON_SCRIPTS_BASE_FOLDER, 'static', 'ephemeris')

WITTY_PI_FOLDER = os.path.join(USER_FOLDER, 'wittypi')

SCHEDULE_SCRIPT_PATH = os.path.join(WITTY_PI_FOLDER, 'runScript.sh')
SCHEDULE_FILE_PATH = os.path.join(WITTY_PI_FOLDER, 'schedule.wpi')

DELAY_BEFORE_SHUTDOWN = 5

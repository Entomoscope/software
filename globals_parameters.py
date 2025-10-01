import os

from datetime import datetime, timedelta

import logging
from logging.handlers import RotatingFileHandler

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

today_log_path = os.path.join(LOGS_DESKTOP_FOLDER, TODAY)
if not os.path.exists(today_log_path):
    os.mkdir(today_log_path)

logger = logging.getLogger('entomoscope_global_param')

filename = os.path.join(today_log_path, TODAY + '_' + this_script + '.log')
h = RotatingFileHandler(filename, mode="a", maxBytes=25000, backupCount=100, encoding="utf-8")
f = logging.Formatter('%(asctime)s;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
h.setFormatter(f)
logger.addHandler(h)
logger.setLevel("DEBUG")

logger.info('today: ' + TODAY)
logger.info('tomorrow: ' + TOMORROW)

logger.info('user folder: ' + USER_FOLDER)
logger.info('user: ' + USER)
logger.info('desktop folder: ' + DESKTOP_FOLDER)

logger.info('logs desktop folder: ' + LOGS_DESKTOP_FOLDER)

EXTERNAL_DISK_FOLDER = os.path.join('/media', USER, 'ENTO_EXT_DISK')

if not os.path.exists(EXTERNAL_DISK_FOLDER):
    DATA_FOLDER = os.path.join(DESKTOP_FOLDER, 'Data')
    if not os.path.exists(DATA_FOLDER):
        os.mkdir(DATA_FOLDER)
else:
    DATA_FOLDER = EXTERNAL_DISK_FOLDER

logger.info('data folder: ' + DATA_FOLDER)

SAVE_FOLDER = os.path.join(DATA_FOLDER, TODAY)

if not os.path.exists(SAVE_FOLDER):
    try:
        os.mkdir(SAVE_FOLDER)
        save_folder_created = True
    except PermissionError as e:
        logger.error(str(e))
        save_folder_created = False
else:
    save_folder_created = True

if not save_folder_created:

    DATA_FOLDER = os.path.join(DESKTOP_FOLDER, 'Data')
    if not os.path.exists(DATA_FOLDER):
        os.mkdir(DATA_FOLDER)

    SAVE_FOLDER = os.path.join(DATA_FOLDER, TODAY)
    if not os.path.exists(SAVE_FOLDER):
        os.mkdir(SAVE_FOLDER)

logger.info('save folder: ' + SAVE_FOLDER)

SOUNDS_CAPTURE_FOLDER = os.path.join(SAVE_FOLDER, 'Sounds')
if not os.path.exists(SOUNDS_CAPTURE_FOLDER):
    os.mkdir(SOUNDS_CAPTURE_FOLDER)

logger.info('sounds capture folder: ' + SOUNDS_CAPTURE_FOLDER)

IMAGES_CAPTURE_FOLDER = os.path.join(SAVE_FOLDER, 'Images')
if not os.path.exists(IMAGES_CAPTURE_FOLDER):
    os.mkdir(IMAGES_CAPTURE_FOLDER)

logger.info('images capture folder: ' + IMAGES_CAPTURE_FOLDER)

ENVIRONMENT_MONITORING_FOLDER = os.path.join(SAVE_FOLDER, 'Environment')
if not os.path.exists(ENVIRONMENT_MONITORING_FOLDER):
    os.mkdir(ENVIRONMENT_MONITORING_FOLDER)

logger.info('environment monitoring folder: ' + ENVIRONMENT_MONITORING_FOLDER)

TMP_FOLDER = os.path.join(PYTHON_SCRIPTS_BASE_FOLDER, 'tmp')

logger.info('tmp folder: ' + TMP_FOLDER)

AI_MODEL_FILE = 'arthropod_dectector_wave18_best.pt'
AI_MODEL_PATH = os.path.join(PYTHON_SCRIPTS_BASE_FOLDER, 'ai_models')
AI_MODEL = os.path.join(AI_MODEL_PATH, AI_MODEL_FILE)

logger.info('ai model file: ' + AI_MODEL_FILE)
logger.info('ai model path: ' + AI_MODEL_PATH)
logger.info('ai model: ' + AI_MODEL)

EPHEMERIS_FILE_PATH = os.path.join(PYTHON_SCRIPTS_BASE_FOLDER, 'static', 'ephemeris')

logger.info('ephemeris file path: ' + EPHEMERIS_FILE_PATH)

WITTY_PI_FOLDER = os.path.join(USER_FOLDER, 'wittypi')

logger.info('witty pi folder: ' + WITTY_PI_FOLDER)

SCHEDULE_SCRIPT_PATH = os.path.join(WITTY_PI_FOLDER, 'runScript.sh')
SCHEDULE_FILE_PATH = os.path.join(WITTY_PI_FOLDER, 'schedule.wpi')

DELAY_BEFORE_SHUTDOWN = 5

logger.info(f'delay before shutdown: {DELAY_BEFORE_SHUTDOWN} seconds')

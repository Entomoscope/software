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
if not os.path.exists(DESKTOP_FOLDER):
    os.mkdir(DESKTOP_FOLDER)

LOGS_DESKTOP_FOLDER = os.path.join(DESKTOP_FOLDER, 'Logs')
if not os.path.exists(LOGS_DESKTOP_FOLDER):
    os.mkdir(LOGS_DESKTOP_FOLDER)

today_log_path = os.path.join(LOGS_DESKTOP_FOLDER, TODAY)
if not os.path.exists(today_log_path):
    os.mkdir(today_log_path)

logger = logging.getLogger('entomoscope_global_param')

filename = os.path.join(today_log_path, TODAY + '_' + this_script + '.log')
h = RotatingFileHandler(filename, mode="a", maxBytes=25000, backupCount=100, encoding="utf-8")
f = logging.Formatter('%(asctime)s.%(msecs)03d;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
h.setFormatter(f)
logger.addHandler(h)
logger.setLevel("DEBUG")

logger.info('****************************')

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

AI_ENABLE = True
logger.info(f'ai enable: {AI_ENABLE}')

AI_MODEL_PATH = os.path.join(PYTHON_SCRIPTS_BASE_FOLDER, 'ai_models')
logger.info('ai model path: ' + AI_MODEL_PATH)

CAPTURE_AI_DETECTION = True
logger.info(f'capture ai detection: {CAPTURE_AI_DETECTION}')

EPHEMERIS_FILE_PATH = os.path.join(PYTHON_SCRIPTS_BASE_FOLDER, 'static', 'ephemeris')
logger.info('ephemeris file path: ' + EPHEMERIS_FILE_PATH)

WITTY_PI_FOLDER = os.path.join(USER_FOLDER, 'wittypi')
logger.info('witty pi folder: ' + WITTY_PI_FOLDER)

SCHEDULE_SCRIPT_PATH = os.path.join(WITTY_PI_FOLDER, 'runScript.sh')
SCHEDULE_FILE_PATH = os.path.join(WITTY_PI_FOLDER, 'schedule.wpi')

MINUTES_OFFSET_FOR_STARTING_ON_TIME = 1 # minutes
logger.info(f'offset for starting on time: {MINUTES_OFFSET_FOR_STARTING_ON_TIME} minutes')

CAMERA_PREVIEW_FPS = 25
logger.info(f'camera preview fps: {CAMERA_PREVIEW_FPS}')

DELAY_BEFORE_SHUTDOWN = 5 # seconds
logger.info(f'delay before shutdown: {DELAY_BEFORE_SHUTDOWN} seconds')

MICROPHONE_DETECTION_INTERVAL = 5 # seconds
logger.info(f'microphone detection interval: {MICROPHONE_DETECTION_INTERVAL} seconds')
MICROPHONE_DETECTION_NUM_TRIES = 15
logger.info(f'microphone detection number of tries: {MICROPHONE_DETECTION_NUM_TRIES}')
MICROPHONE_STARTUP_DELAY_BEFORE_FIST_CAPTURE = 10 # seconds
logger.info(f'microphone startup delay before first capture: {MICROPHONE_STARTUP_DELAY_BEFORE_FIST_CAPTURE} seconds')

WIFI_CONNECTION_TRY_DURATION = 5 # seconds
logger.info(f'wifi connection try duration: {WIFI_CONNECTION_TRY_DURATION} seconds')
INTERNET_CONNECTION_TRY_DURATION = 5 # seconds
logger.info(f'internet connection try duration: {INTERNET_CONNECTION_TRY_DURATION} seconds')
WIFI_AUTOCONNECT_AP = True
logger.info(f'wifi AP autoconnection set to: {WIFI_AUTOCONNECT_AP}')

LOW_BATTERY_VOLTAGE_TRESHOLD = 10.5 # volts

SERVER_PORT = 7777
logger.info(f'server port: {SERVER_PORT}')
SERVER_DEBUG = True
logger.info(f'server debug mode: {SERVER_DEBUG}')
SERVER_ALLOWED_EXTENSIONS = {'csv', 'json'}

#! /usr/bin/python3

import os
import shutil
from datetime import datetime, timedelta, timezone

from shutil import rmtree, copytree

import traceback

from time import time, sleep

from flask import Flask, make_response, render_template, Response, jsonify, request, redirect, url_for
from werkzeug.utils import secure_filename

# from flask_socketio import SocketIO

import copy

from json import load

import numpy as np
import cv2

import logging
from logging.handlers import RotatingFileHandler

import base64

import libcamera

from crontab_management import CrontabManagement

from configuration2 import Configuration2

from peripherals.pinout2 import IMAGES_CAPTURE_ACTIVITY_PIN, SOUNDS_CAPTURE_ACTIVITY_PIN, SHUTDOWN_PIN, STARTUP_PIN, LEDS_FRONT_PIN, LEDS_REAR_DEPORTED_UV_PIN
from peripherals.rpi import Rpi
from peripherals.storage import Storage
from peripherals.leds import Leds
from peripherals.camera2 import Camera2
from peripherals.gnss2 import Gnss2
from peripherals.microphone2 import Microphone2
from peripherals.wittypi import WittyPi
from peripherals.wifi import Wifi

from focus import Focus

from ephemeris import Ephemeris

from date_time import DateTime

from globals_parameters import USER, SERVER_PORT, SERVER_DEBUG, SERVER_ALLOWED_EXTENSIONS, TODAY_NOW, AI_ENABLE, AI_MODEL_PATH, CAPTURE_AI_DETECTION, PYTHON_SCRIPTS_BASE_FOLDER, TMP_FOLDER, IMAGES_CAPTURE_FOLDER, SOUNDS_CAPTURE_FOLDER, TODAY, TOMORROW, LOGS_DESKTOP_FOLDER, WITTY_PI_FOLDER, DATA_FOLDER, MINUTES_OFFSET_FOR_STARTING_ON_TIME, CAMERA_PREVIEW_FPS

from firmware import updates_check, updates_get, get_last_commit

import pigpio

this_script = os.path.basename(__file__)[:-3]

today_log_path = os.path.join(LOGS_DESKTOP_FOLDER, TODAY)
if not os.path.exists(today_log_path):
    os.mkdir(today_log_path)

filename = os.path.join(today_log_path, TODAY + '_' + this_script + '.log')
h = RotatingFileHandler(filename, mode="a", maxBytes=25000, backupCount=100, encoding="utf-8")
f = logging.Formatter('%(asctime)s.%(msecs)03d;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
h.setFormatter(f)

app = Flask(__name__)
# app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
# app.config['SERVER_NAME'] = 'entomoscope:7777'

# socketio = SocketIO(app)

app.logger.addHandler(h)
app.logger.setLevel("DEBUG")

werkzeug_logger = logging.getLogger("werkzeug")

filename = os.path.join(today_log_path, TODAY + '_' + 'werkzeug.log')
h = RotatingFileHandler(filename, mode="a", maxBytes=100000, backupCount=100, encoding="utf-8")
f = logging.Formatter('%(asctime)s.%(msecs)03d;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
h.setFormatter(f)
werkzeug_logger.addHandler(h)
werkzeug_logger.setLevel("DEBUG")

app.config['UPLOAD_FOLDER'] = PYTHON_SCRIPTS_BASE_FOLDER

pi = pigpio.pi()

def isStartupCompleted():

    return pi.read(STARTUP_PIN)

def isSignalToShutdownReceived():

    return pi.read(SHUTDOWN_PIN)

app.logger.info('****************************')

app.logger.info(f'server script started with pid {os.getpid()}')

app.logger.info('wait for startup script to complete')

while not isStartupCompleted():
    # Si la broche SHUTDOWN_PIN passe à l'état haut => arret script server
    if isSignalToShutdownReceived():
        app.logger.info('shutdown signal received')
        app.logger.info('server script stopped')
        exit()
    sleep(0.5)

app.logger.info('startup script completed')

crontab_management = CrontabManagement()

if pi.read(SHUTDOWN_PIN) == 1:

    images_capture_state = 'stopped'
    sounds_capture_state = 'stopped'

else:

    if pi.read(IMAGES_CAPTURE_ACTIVITY_PIN) == 0:
        images_capture_state = 'running'
    else:
        images_capture_state = 'paused'

    if pi.read(SOUNDS_CAPTURE_ACTIVITY_PIN) == 0:
        sounds_capture_state = 'running'
    else:
        sounds_capture_state = 'paused'

configuration = Configuration2()
configuration.read()
app.logger.info('configuration read')

rpi = Rpi()

try:

    # IA seulement disponible sur OS 64-bit
    if rpi.arch_version == '64-bit':

        from ultralytics.utils.plotting import Annotator, colors
        from ultralytics.utils.ops import xywhn2xyxy

        if AI_ENABLE:

            app.logger.info('64-bit arch => AI available')

            if configuration.ai_detection['file']:
                ai_model_file = os.path.join(AI_MODEL_PATH, configuration.ai_detection['file'])
            else:
                ai_model_files = os.listdir(AI_MODEL_PATH)
                if len(ai_model_files) > 0:
                    ai_model_file = os.path.join(AI_MODEL_PATH, ai_model_files[0])
                    app.logger.warning(f'no AI model file in config file')
                    app.logger.warning(f'use {ai_model_files[0]} by default')
                    configuration.ai_detection['file'] = ai_model_files[0]
                    configuration.save()
                else:
                  ai_model_file = None
                  AI_AVAILABLE = False
                  app.logger.warning(f'no AI model file found in {AI_MODEL_PATH}')
                  app.logger.warning(f'AI disabled')

            if ai_model_file:

                AI_AVAILABLE = True
                start_time = datetime.now()
                from ultralytics import YOLO
                elapsed_time = datetime.now() - start_time
                app.logger.info(f"YOLO import time: {elapsed_time.seconds + 1} seconds")
                start_time = datetime.now()
                ai_model = YOLO(ai_model_file)
                elapsed_time = datetime.now() - start_time
                app.logger.info(f"AI model file loaded: {configuration.ai_detection['file']}")
                app.logger.info(f"AI model file loading time: {elapsed_time.seconds}.{elapsed_time.microseconds} seconds")

        else:

            AI_AVAILABLE = False
            app.logger.info('64-bit arch => AI available but manualy disabled')

    else:

        AI_AVAILABLE = False
        app.logger.info('32-bit arch => AI not available')

except BaseException as e:

    AI_AVAILABLE = False
    app.logger.info('unable to manage AI => AI not available')
    logger.error(str(e))

sd_card = Storage('sd')

external_disk = Storage('external_disk')
if not external_disk.available:
    app.logger.warning('external disk not found')

gnss = None

dateTime = DateTime()

tzone = datetime.now().astimezone().strftime('%Z')

witty_pi = WittyPi()

if witty_pi.available:
    witty_pi.get_input_voltage()
    battery_level = witty_pi.input_voltage
else:
    battery_level = 0.0
    app.logger.warning('Witty Pi not detected')

leds_intensity = [configuration.leds['intensity_front'], configuration.leds['intensity_rear_deported_uv']]
leds_delays = [configuration.leds['delay_on'], configuration.leds['delay_off']]
leds_always_on = configuration.leds['always_on']

capture_mode = configuration.mode['mode']

autofocus = {'mode': configuration.camera['autofocus']['mode'], 'lens_position': configuration.camera['autofocus']['lens_position']}

white_balance = {'enable': configuration.camera['auto_white_balance']['enable'], 'mode': configuration.camera['auto_white_balance']['mode']}

jpeg_quality = configuration.files['jpeg_quality']

periodicity = configuration.schedule['periodicity']

crop_limits = configuration.camera['sensor']['crop_limits']

auto_exposure_gain = {'enable': configuration.camera['auto_exposure_gain']['enable'], 'mode': configuration.camera['auto_exposure_gain']['mode'], 'exposure_time': configuration.camera['auto_exposure_gain']['exposure_time'], 'exposure_value': configuration.camera['auto_exposure_gain']['exposure_value']}

camera_model = configuration.camera['model']
sensor_resolution = [configuration.camera['sensor']['resolution'][0], configuration.camera['sensor']['resolution'][1]]
preview_resolution = [configuration.camera['sensor']['width_preview'], configuration.camera['sensor']['height_preview']]
sensor_mode = [configuration.camera['sensor']['preview_mode'], configuration.camera['sensor']['capture_mode']]

focus_measure_enable = configuration.camera['autofocus']['measure_enable']
focus_measure_mode = configuration.camera['autofocus']['measure_mode']

multifocus_mode = configuration.images_capture['multifocus']['enable']
lens_position_offset = configuration.images_capture['multifocus']['lens_position_offset']

server_settings = {'keep_image_center': configuration.server['image_constraints']['centered'], 'keep_image_square': configuration.server['image_constraints']['square'], 'preview_max_width': configuration.server['preview_size']['max_width']}

ai_detection = {'enable': configuration.ai_detection['enable'],
                'file': configuration.ai_detection['file'],
                'image_scale': configuration.ai_detection['image_scale'],
                'min_confidence': configuration.ai_detection['min_confidence'],
                'image_width': configuration.ai_detection['image_width'],
                'image_height': configuration.ai_detection['image_height']}
ai_boxes_color = [(255,85,0), (255,170,0), (255,255,0), (170,255,85), (85,255,170), (0,255,255), (0,170,255), (0,85,255), (0,0,255), (0,0,170)]

current_lens_position = 0.0

focus = Focus()

capture_next_image = False

data_current_directory = DATA_FOLDER
data_current_file = None
show_preview_file = False
show_preview_image = False
show_preview_sound = False
file_data = None
file_caption = None

logs_current_directory = LOGS_DESKTOP_FOLDER
logs_current_file = None
show_preview_log = False
log_data = None

wifi = Wifi(rpi.uuid)
wifi.list()

pause_stream = False

camera = None
microphone = None
leds_rear_deported_uv = None
leds_front = None

updates_available = False
updates_available = updates_check()
app.logger.info(f'updates available? {updates_available}')

@app.route('/')
def index():

    global camera, leds_front, leds_rear_deported_uv, images_capture_state, sounds_capture_state, gnss, microphone, sd_card, external_disk, wifi

    get_captures_state()

    configuration.read()
    app.logger.info('configuration read')

    if images_capture_state == 'stopped':

        if camera:
            camera.stop()
            camera.camera.close()
            camera = None
            app.logger.info('camera stopped')

        if leds_front:
            leds_front.turn_off()
            leds_front = None
            app.logger.info('LEDs front stopped')

        if leds_rear_deported_uv:
            leds_rear_deported_uv.turn_off()
            leds_rear_deported_uv = None
            app.logger.info('LEDs rear/UV/deported stopped')

    elif images_capture_state == 'paused':

        if leds_front:
            leds_front.turn_off()
            leds_front = None
            app.logger.info('LEDs front stopped')

        if leds_rear_deported_uv:
            leds_rear_deported_uv.turn_off()
            leds_rear_deported_uv = None
            app.logger.info('LEDs rear/UV/deported stopped')

    if sounds_capture_state == 'stopped':

        if microphone:
            microphone.stop()
            microphone = None
            app.logger.info('microphone stopped')

    sd_card.get_data()
    external_disk.find()
    external_disk.get_data()

    app.logger.info('storage updated')

    if gnss:
        gnss.stop()
        gnss = None
        app.logger.info('GNSS stopped')

    if witty_pi.available:
        witty_pi.get_input_voltage()
        battery_level = witty_pi.input_voltage
    else:
        battery_level = 0.0
        app.logger.warning('Witty Pi not detected')

    startup_num = datetime.strptime(configuration.schedule['next_startup'], '%Y-%m-%d %H:%M')
    shutdown_num = datetime.strptime(configuration.schedule['next_shutdown'], '%Y-%m-%d %H:%M')
    now = datetime.now()

    # print(startup_num)
    # print(shutdown_num)
    # print(now)

    days = []
    s_days = []
    day_start_found = False
    day_start_index = 0

    for i in range(0, 21):

        s_now = now + timedelta(days=i)

        if s_now.day == startup_num.day:
            day_start_found = True
            day_start_index = i
            k = 0
        if not day_start_found:
            s_days.append(False)
        else:
            if configuration.schedule['periodicity'] == 'every_day':
                s_days.append(True)
            elif configuration.schedule['periodicity'] == 'every_other_day':
                if k % 2 == 0:
                    s_days.append(True)
                else:
                    s_days.append(False)
            elif configuration.schedule['periodicity'] == 'every_week':
                if k % 7 == 0:
                    s_days.append(True)
                else:
                    s_days.append(False)
            k += 1

        if i == 0:
            days.append('Today')
        else:
            days.append(s_now.strftime('%a %m/%d'))

    # print(days)
    # print(s_days)

    # print(day_start_index)

    if configuration.schedule['enable']:

        hours, minutes = [int(x) for x in configuration.schedule['next_startup'].split(' ')[1].split(':')]
        s = 100 * (hours*60 + minutes) // 1440
        hours, minutes = [int(x) for x in configuration.schedule['next_shutdown'].split(' ')[1].split(':')]
        e = 100 * (hours*60 + minutes) // 1440
        if e == 0:
            e = 100

        if e > s:
            schedule = [s, e-s, 100 - e]
            color = [0, 1, 0]
        else:
            schedule1 = [0, s, 100 - s]
            color1 = [0, 0, 1]
            schedule2 = [e, 100-e, 0]
            color2 = [1, 0, 0]

        if configuration.schedule['periodicity'] == 'every_day':
            k = 1
        elif configuration.schedule['periodicity'] == 'every_other_day':
            k = 2
        elif configuration.schedule['periodicity'] == 'every_week':
            k = 7

        schedules = []
        colors = []

        d = 0
        k_set = False
        for i in range(0, 21):

            if i >= day_start_index:

                if d % k == 0:

                    if e > s:

                        schedules.append([s, e-s, 100 - e])
                        colors.append([0, 1, 0])

                    else:

                        if i == day_start_index:

                            schedules.append([0, s, 100 - s])
                            colors.append([0, 0, 1])

                            k_set = True

                        else:

                            if k == 1:

                                schedules.append([e, s-e, 100 - s])
                                colors.append([1, 0, 1])

                            else:

                                schedules.append([0, s, 100 - s])
                                colors.append([0, 0, 1])

                                k_set = True

                else:

                    if k_set:
                        k_set = False
                        schedules.append([e, 100-e, 0])
                        colors.append([1, 0, 0])
                    else:
                        schedules.append([0, 0, 0])
                        colors.append([0, 0, 0])

                d += 1

            else:

                schedules.append([0, 0, 0])
                colors.append([0, 0, 0])

        # print(schedules)
        # print(colors)

        if configuration.images_capture['enable']:
            images_capture = {'s_days': s_days, 'schedules': schedules, 'colors': colors}
        else:
            images_capture = {'s_days': [False]*len(s_days), 'schedules': [False]*len(s_days), 'colors': [False]*len(s_days)}

        if configuration.sounds_capture['enable']:
            sounds_capture = {'s_days': s_days, 'schedules': schedules, 'colors': colors}
        else:
            sounds_capture = {'s_days': [False]*len(s_days), 'schedules': [False]*len(s_days), 'colors': [False]*len(s_days)}

    else:

        s_days = [False]*len(s_days)
        schedules = [False]*len(s_days)
        colors = [False]*len(s_days)

        images_capture = []
        sounds_capture = []

    return make_response(render_template('index.html', zip=zip, configuration=configuration, updates_available=updates_available, days=days, images_capture=images_capture, sounds_capture=sounds_capture, rpi=rpi, tzone=tzone, wifi=wifi, sd_card=sd_card, external_disk=external_disk, battery_level=battery_level, gnss=gnss, dateTime=dateTime, images_capture_state=images_capture_state, sounds_capture_state=sounds_capture_state))


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in SERVER_ALLOWED_EXTENSIONS


@app.route('/', methods=['POST'])
def upload_configuration_file():

    try:

        if 'file' in request.files:

            uploaded_file = request.files['file']

            if uploaded_file.filename == '':
                return 'No selected file', 400

            if uploaded_file and not allowed_file(uploaded_file.filename):
                return 'File type not allowed', 400

            if uploaded_file:

                filename = secure_filename(uploaded_file.filename)

                try:

                    if uploaded_file.filename == 'configuration.json':
                        uploaded_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                        app.logger.info('configuration file sent to the entomoscope')
                    elif uploaded_file.filename == 'ephemeris.csv':
                        uploaded_file.save(os.path.join(app.config['UPLOAD_FOLDER'], 'static', 'ephemeris', filename))
                        app.logger.info('ephemeris file sent to the entomoscope')
                    return redirect('/')

                except BaseException as e:

                    app.logger.error(str(e))
                    return f'Error sending file to the entomoscope: {str(e)}', 500

    except BaseException as e:

        app.logger.error(str(e))

        return f'Error uploading configuration file: {str(e)}', 500


@app.route('/data')
def data():

    global camera, leds_front, leds_rear_deported_uv, gnss, microphone, data_current_directory, data_current_file, show_preview_file, show_preview_image, show_preview_sound, file_data, file_caption

    get_captures_state()

    if images_capture_state == 'stopped':

        if camera:
            camera.stop()
            camera.camera.close()
            camera = None
            app.logger.info('camera stopped')

        if leds_front:
            leds_front.turn_off()
            leds_front = None
            app.logger.info('LEDs front stopped')

        if leds_rear_deported_uv:
            leds_rear_deported_uv.turn_off()
            leds_rear_deported_uv = None
            app.logger.info('LEDs rear/UV/deported stopped')

    elif images_capture_state == 'paused':

        if leds_front:
            leds_front.turn_off()
            leds_front = None
            app.logger.info('LEDs front stopped')

        if leds_rear_deported_uv:
            leds_rear_deported_uv.turn_off()
            leds_rear_deported_uv = None
            app.logger.info('LEDs rear/UV/deported stopped')

    if gnss:
        gnss.stop()
        gnss = None
        app.logger.info('GNSS stopped')

    if sounds_capture_state == 'stopped':

        if microphone:
            microphone.stop()
            microphone = None
            app.logger.info('microphone stopped')

    rpi.cpu_temperature = rpi.get_temperature()

    if witty_pi.available:
        witty_pi.get_input_voltage()
        battery_level = witty_pi.input_voltage
    else:
        battery_level = 0.0
        app.logger.warning('Witty Pi not detected')

    sd_card.get_data()

    if os.path.exists(data_current_directory):

        files = sorted(os.listdir(data_current_directory), reverse=True)
        isdirs = [os.path.isdir(os.path.join(data_current_directory, x)) for x in files]
        isconfs = [x.startswith('configuration') for x in files]
        isimages = [x.endswith('jpg') for x in files]
        istopdir = data_current_directory == DATA_FOLDER

    else:

        files = None
        isdirs = None
        isconfs = None
        isimages = None
        istopdir = None

        app.logger.error(f'no directory {data_current_directory}')

    return make_response(render_template('data.html', updates_available=updates_available, files=files, isdirs=isdirs, isconfs=isconfs, isimages=isimages, zip=zip, istopdir=istopdir, show_preview_file=show_preview_file, show_preview_image=show_preview_image, show_preview_sound=show_preview_sound, data_current_file=data_current_file, file_data=file_data, file_caption=file_caption, rpi=rpi, battery_level=battery_level, sd_card=sd_card))


@app.route('/storage', methods=['GET', 'POST'])
def storage():

    global camera, leds_front, leds_rear_deported_uv, gnss, microphone, data_current_directory, data_current_file, show_preview_file, show_preview_image, show_preview_sound, file_data, file_caption

    get_captures_state()

    if images_capture_state == 'stopped':

        if camera:
            camera.stop()
            camera.camera.close()
            camera = None
            app.logger.info('camera stopped')

        if leds_front:
            leds_front.turn_off()
            leds_front = None
            app.logger.info('LEDs front stopped')

        if leds_rear_deported_uv:
            leds_rear_deported_uv.turn_off()
            leds_rear_deported_uv = None
            app.logger.info('LEDs rear/UV/deported stopped')

    elif images_capture_state == 'paused':

        if leds_front:
            leds_front.turn_off()
            leds_front = None
            app.logger.info('LEDs front stopped')

        if leds_rear_deported_uv:
            leds_rear_deported_uv.turn_off()
            leds_rear_deported_uv = None
            app.logger.info('LEDs rear/UV/deported stopped')

    if gnss:
        gnss.stop()
        gnss = None
        app.logger.info('GNSS stopped')

    if sounds_capture_state == 'stopped':

        if microphone:
            microphone.stop()
            microphone = None
            app.logger.info('microphone stopped')

    rpi.cpu_temperature = rpi.get_temperature()

    if witty_pi.available:
        witty_pi.get_input_voltage()
        battery_level = witty_pi.input_voltage
    else:
        battery_level = 0.0
        app.logger.warning('Witty Pi not detected')

    sd_card.get_data()
    external_disk.find()
    external_disk.get_data()

    stats = None

    try:

        stats = get_data_folders_stats()

    except BaseException as e :

        app.logger.error(str(e))

    return make_response(render_template('storage.html', updates_available=updates_available, stats=stats, external_disk=external_disk, zip=zip, rpi=rpi, battery_level=battery_level, sd_card=sd_card))


@app.route('/manage_data/<action>/<value>')
def manage_data(action, value):

    global data_current_directory, data_current_file, show_preview_file, show_preview_image, show_preview_sound, file_data, file_caption

    app.logger.info(f'manage_data() {action} {value}')

    try:

        if action == 'chdir':

            if value == 'up':

                data_current_directory = '/'.join(data_current_directory.split('/')[0:-1])

                if not data_current_directory:
                    data_current_directory = '/'

                show_preview_file = False
                show_preview_image = False
                show_preview_sound = False
                file_data = None
                file_caption = None

            else:

                data_current_directory = os.path.join(data_current_directory, value)

            data_current_file = None

        elif action == 'show':

            file_path = os.path.join(data_current_directory, value)

            data_current_file = value

            if value.endswith('.json') or value.endswith('.txt') or value.endswith('.csv') or value.endswith('.log'):

                with open(file_path, 'r') as f:
                    file_data = f.read()

                if not file_data:
                    file_data = 'File empty'
                    file_caption = ''

                show_preview_file = True
                show_preview_image = False
                show_preview_sound = False

            elif value.endswith('.jpg'):

                json_file = file_path.replace('.jpg', '.json')

                if rpi.arch_version == '64-bit' and os.path.exists(json_file):

                    json_file = file_path.replace('.jpg', '.json')

                    with open(json_file, 'r') as f:
                        json_data = load(f)

                    if json_data['EntomoscopeAiPredictionNumBoxes'] > 0:

                        frame = cv2.imread(file_path)

                        ann = Annotator(
                            frame,
                            line_width=None,  # default auto-size
                            font_size=None,  # default auto-size
                            font="Arial.ttf",  # must be ImageFont compatible
                            pil=False,  # use PIL, otherwise uses OpenCV
                        )

                        box_xyxyn = [0,0,0,0]
                        box_xyxy = [0,0,0,0]

                        file_caption = ' ' + f"{json_data['EntomoscopeAiPredictionNumBoxes']}" + ' box' + ('es' if json_data['EntomoscopeAiPredictionNumBoxes']>0 else '') + ' in ' f"{json_data['EntomoscopeAiPredictionSpeed']}" + 'ms'

                        for i in range(0, json_data['EntomoscopeAiPredictionNumBoxes']):

                            box_xywhn = json_data['EntomoscopeAiPredictionBoxes'][i]
                            conf = json_data['EntomoscopeAiPredictionConf'][i]
                            if json_data['EntomoscopeAiPredictionLabels']:
                                label = json_data['EntomoscopeAiPredictionLabels'][i]
                            else:
                                label = ''

                            box_xyxyn[0] = box_xywhn[0] - box_xywhn[2] / 2
                            box_xyxyn[1] = box_xywhn[1] - box_xywhn[3] / 2
                            box_xyxyn[2] = box_xywhn[0] + box_xywhn[2] / 2
                            box_xyxyn[3] = box_xywhn[1] + box_xywhn[3] / 2

                            # box_xyxy[0] = box_xyxyn[0] * json_data['ScalerCrop'][2]
                            # box_xyxy[1] = box_xyxyn[1] * json_data['ScalerCrop'][3]
                            # box_xyxy[2] = box_xyxyn[2] * json_data['ScalerCrop'][2]
                            # box_xyxy[3] = box_xyxyn[3] * json_data['ScalerCrop'][3]

                            box_xyxy[0] = box_xyxyn[0] * frame.shape[1]
                            box_xyxy[1] = box_xyxyn[1] * frame.shape[0]
                            box_xyxy[2] = box_xyxyn[2] * frame.shape[1]
                            box_xyxy[3] = box_xyxyn[3] * frame.shape[0]

                            # https://docs.ultralytics.com/reference/utils/ops/#ultralytics.utils.ops.xywhn2xyxy
                            # def xywhn2xyxy(x, w: int = 640, h: int = 640, padw: int = 0, padh: int = 0)
                            # x	np.ndarray | torch.Tensor
                            # box_xyxy = xywhn2xyxy(box_xywhn, json_data['ScalerCrop'][2], json_data['ScalerCrop'][3])

                            ann.box_label(box_xyxy, f'{label} {conf:.2f}', color=colors(0, bgr=True))

                        frame = ann.result()

                        img_encode = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality])[1]

                        file_data = base64.b64encode(img_encode).decode('utf-8')

                    else:

                        with open(file_path, 'rb') as f:
                            file_data = f.read()

                        file_data = base64.b64encode(file_data).decode('utf-8')

                else:

                    with open(file_path, 'rb') as f:
                        file_data = f.read()

                    file_data = base64.b64encode(file_data).decode('utf-8')

                show_preview_file = False
                show_preview_image = True
                show_preview_sound = False

            elif value.endswith('.wav'):

                shutil.copy(file_path, os.path.join(PYTHON_SCRIPTS_BASE_FOLDER, 'static', 'tmp.wav'))

                show_preview_file = False
                show_preview_image = False
                show_preview_sound = True

    except BaseException as e:

        app.logger.error(str(e))

    return redirect('/data')


@app.route('/manage_storage/<action>/<value>', methods=['GET', 'POST'])
def manage_storage(action, value):

    global data_current_file, show_preview_file, show_preview_image, show_preview_sound, file_data, file_caption

    app.logger.info(f'manage_storage() {action} {value}')

    try:

        data = []

        if action == 'delete':

            try:

                if value == 'all':
                    rmtree(DATA_FOLDER)
                    os.mkdir(DATA_FOLDER)
                else:
                    rmtree(os.path.join(DATA_FOLDER, value))

            except BaseException as e:
                app.logger.error(str(e))

            sleep(1)

            app.logger.info(f'manage_storage() {action} {value} done')

            sd_card.get_data()

            stats = get_data_folders_stats()

            data = [sd_card.used, sd_card.used_num, sd_card.used_percent, sd_card.used_percent_num, stats['total']]

            # socketio.send('file deleted')

        elif action == 'save':

            try:

                external_disk_data_path = os.path.join(external_disk.path, 'data_' + rpi.uuid)

                if not os.path.exists(external_disk_data_path):
                    os.mkdir(external_disk_data_path)

                copytree(os.path.join(DATA_FOLDER, value), os.path.join(external_disk_data_path, value), dirs_exist_ok=True)

                external_disk.get_data()
                data = [external_disk.used, external_disk.used_num, external_disk.used_percent, external_disk.used_percent_num]

            except BaseException as e:
                app.logger.error(str(e))

            sleep(1)

            app.logger.info(f'manage_storage() {action} {value} done')

        return jsonify(success=True, message='Success', data=data)

    except BaseException as e:

        app.logger.error(str(e))

        return jsonify(success=False, message='Error', data=str(e))


@app.route('/global_settings')
def global_settings():

    global camera, leds_front, leds_rear_deported_uv, gnss, microphone

    get_captures_state()

    if images_capture_state == 'stopped':

        if camera:
            camera.stop()
            camera.camera.close()
            camera = None
            app.logger.info('camera stopped')

        if leds_front:
            leds_front.turn_off()
            leds_front = None
            app.logger.info('LEDs front stopped')

        if leds_rear_deported_uv:
            leds_rear_deported_uv.turn_off()
            leds_rear_deported_uv = None
            app.logger.info('LEDs rear/UV/deported stopped')

    elif images_capture_state == 'paused':

        if leds_front:
            leds_front.turn_off()
            leds_front = None
            app.logger.info('LEDs front stopped')

        if leds_rear_deported_uv:
            leds_rear_deported_uv.turn_off()
            leds_rear_deported_uv = None
            app.logger.info('LEDs rear/UV/deported stopped')

    if gnss:
        gnss.stop()
        gnss = None
        app.logger.info('GNSS stopped')

    if sounds_capture_state == 'stopped':

        if microphone:
            microphone.stop()
            microphone = None
            app.logger.info('microphone stopped')

    rpi.cpu_temperature = rpi.get_temperature()

    if witty_pi.available:
        witty_pi.get_input_voltage()
        battery_level = witty_pi.input_voltage
    else:
        battery_level = 0.0
        app.logger.warning('Witty Pi not detected')

    rpi.wifi_ssid = rpi.get_wifi_ssid()
    rpi.ip_address = rpi.get_ip_address()
    rpi.cpu_temperature = rpi.get_temperature()

    sd_card.get_data()

    tzone = datetime.now().astimezone().strftime('%Z')

    configuration.read()
    app.logger.info('configuration read')

    startup_date, startup_time = configuration.schedule['next_startup'].split()
    shutdown_date, shutdown_time = configuration.schedule['next_shutdown'].split()

    startup_date = '-'.join([startup_date[:4], startup_date[5:7], startup_date[8:]])
    shutdown_date = '-'.join([shutdown_date[:4], shutdown_date[5:7], shutdown_date[8:]])

    # today = '-'.join([TODAY[:4], TODAY[4:6], TODAY[6:]])
    today = dateTime.get_date()

    startup_num = datetime.strptime(configuration.schedule['next_startup'], '%Y-%m-%d %H:%M')
    shutdown_num = datetime.strptime(configuration.schedule['next_shutdown'], '%Y-%m-%d %H:%M')
    now = datetime.now()

    return make_response(render_template('global_settings.html', configuration=configuration, updates_available=updates_available, today=today, tzone=tzone, date_num=(now,startup_num,shutdown_num), startup=(startup_date, startup_time), shutdown=(shutdown_date, shutdown_time), zip=zip, rpi=rpi, battery_level=battery_level, sd_card=sd_card))


@app.route('/images_capture_settings')
def images_capture_settings():

    global camera, leds_front, leds_rear_deported_uv, gnss, microphone

    try:

        configuration.read()
        app.logger.info('configuration read')

        crop_limits = configuration.camera['sensor']['crop_limits']

        if gnss:
            gnss.stop()
            gnss = None
            app.logger.info('GNSS stopped')

        get_captures_state()

        if sounds_capture_state == 'stopped':

            if microphone:
                microphone.stop()
                microphone = None
                app.logger.info('microphone stopped')

        if images_capture_state == 'stopped':

            if not camera:
                camera = Camera2(configuration=configuration, mode='preview', perf=True)
                if camera and camera.is_camera_supported:
                    camera.start()
                    app.logger.info('camera started')
                    camera_supported = camera.is_camera_supported
                    camera_resolution = camera.get_sensor_resolution()
                    autofocus_available = camera.autofocus_available
                else:
                    app.logger.warning('camera not started because model is not supported')
                    camera_supported = False
                    camera_resolution = None
                    autofocus_available = False
            else:
                app.logger.info('camera already started')
                camera_supported = camera.is_camera_supported
                camera_resolution = camera.get_sensor_resolution()
                autofocus_available = camera.autofocus_available

            if not leds_rear_deported_uv:
                leds_rear_deported_uv = Leds(LEDS_REAR_DEPORTED_UV_PIN)
                leds_rear_deported_uv.set_intensity(configuration.leds['intensity_rear_deported_uv'])
                leds_rear_deported_uv.turn_on()

            if not leds_front:
                leds_front = Leds(LEDS_FRONT_PIN)
                leds_front.set_intensity(configuration.leds['intensity_front'])
                leds_front.turn_on()

            leds_available = True

        elif images_capture_state == 'paused':

            if not leds_rear_deported_uv:
                leds_rear_deported_uv = Leds(LEDS_REAR_DEPORTED_UV_PIN)
                leds_rear_deported_uv.set_intensity(configuration.leds['intensity_rear_deported_uv'])
                leds_rear_deported_uv.turn_on()

            if not leds_front:
                leds_front = Leds(LEDS_FRONT_PIN)
                leds_front.set_intensity(configuration.leds['intensity_front'])
                leds_front.turn_on()

            leds_available = True
            camera_supported = False
            camera_resolution = None
            autofocus_available = False

        else:

            leds_available = False
            camera_supported = False
            camera_resolution = None
            autofocus_available = False

        ai_models = sorted(os.listdir(AI_MODEL_PATH))

        ai_models = [x for x in ai_models if not x.endswith('.onnx')]

        rpi.cpu_temperature = rpi.get_temperature()

        if witty_pi.available:
            witty_pi.get_input_voltage()
            battery_level = witty_pi.input_voltage
        else:
            battery_level = 0.0
            app.logger.warning('Witty Pi not detected')

        sd_card.get_data()

        return make_response(render_template('images_capture_settings.html', updates_available=updates_available, camera_supported=camera_supported, camera_resolution=camera_resolution, autofocus_available=autofocus_available, images_capture_state=images_capture_state, leds_available=leds_available, ai_models=ai_models, configuration=configuration, rpi=rpi, battery_level=battery_level, zip=zip, sd_card=sd_card))

    except BaseException as e:

        app.logger.error(str(e))

        return redirect('/images_capture_settings')

@app.route('/sounds_capture_settings')
def sounds_capture_settings():

    global camera, leds_front, leds_rear_deported_uv, microphone, gnss

    try:

        if gnss:
            gnss.stop()
            gnss = None
            app.logger.info('GNSS stopped')

        get_captures_state()

        if images_capture_state == 'stopped':

            if camera:
                camera.stop()
                camera.camera.close()
                camera = None
                app.logger.info('camera stopped')

            if leds_front:
                leds_front.turn_off()
                leds_front = None
                app.logger.info('LEDs front stopped')

            if leds_rear_deported_uv:
                leds_rear_deported_uv.turn_off()
                leds_rear_deported_uv = None
                app.logger.info('LEDs rear/UV/deported stopped')

        elif images_capture_state == 'paused':

            if leds_front:
                leds_front.turn_off()
                leds_front = None
                app.logger.info('LEDs front stopped')

            if leds_rear_deported_uv:
                leds_rear_deported_uv.turn_off()
                leds_rear_deported_uv = None
                app.logger.info('LEDs rear/UV/deported stopped')

        if sounds_capture_state == 'stopped':
            if microphone:
                microphone.stop()
                microphone = None
                app.logger.info('microphone stopped')
            microphone = Microphone2(configuration.microphone['sample_rate'], configuration.microphone['gain'])
            microphone_available = 1 if not microphone.available else 2
        else:
            if microphone:
                microphone_available = 1 if not microphone.available else 2
            else:
                microphone_available = 0

        if microphone_available == 0:
            app.logger.warning('microphone not available because sounds capture is running')
            microphone_id = ''
            microphone_firmware = ''
        elif microphone_available == 1:
            app.logger.error('microphone not found')
            microphone_id = ''
            microphone_firmware = ''
        else:
            microphone_id = microphone.id
            microphone_firmware = microphone.firmware

        rpi.cpu_temperature = rpi.get_temperature()

        if witty_pi.available:
            witty_pi.get_input_voltage()
            battery_level = witty_pi.input_voltage
        else:
            battery_level = 0.0
            app.logger.warning('Witty Pi not detected')

        sd_card.get_data()

        return make_response(render_template('sounds_capture_settings.html', sounds_capture_state=sounds_capture_state, updates_available=updates_available, microphone_available=microphone_available, microphone_id=microphone_id, microphone_firmware=microphone_firmware, configuration=configuration, rpi=rpi, battery_level=battery_level, sd_card=sd_card))

    except BaseException as e:

        app.logger.error(str(e))

        return redirect('/sounds_capture_settings')

@app.route('/logs')
def logs():

    global camera, leds_front, leds_rear_deported_uv, gnss, microphone, logs_current_directory, logs_current_file, show_preview_log, log_data

    get_captures_state()

    if images_capture_state == 'stopped':

        if camera:
            camera.stop()
            camera.camera.close()
            camera = None
            app.logger.info('camera stopped')

        if leds_front:
            leds_front.turn_off()
            leds_front = None
            app.logger.info('LEDs front stopped')

        if leds_rear_deported_uv:
            leds_rear_deported_uv.turn_off()
            leds_rear_deported_uv = None
            app.logger.info('LEDs rear/UV/deported stopped')

    elif images_capture_state == 'paused':

        if leds_front:
            leds_front.turn_off()
            leds_front = None
            app.logger.info('LEDs front stopped')

        if leds_rear_deported_uv:
            leds_rear_deported_uv.turn_off()
            leds_rear_deported_uv = None
            app.logger.info('LEDs rear/UV/deported stopped')

    if gnss:
        gnss.stop()
        gnss = None
        app.logger.info('GNSS stopped')

    rpi.cpu_temperature = rpi.get_temperature()

    if witty_pi.available:
        witty_pi.get_input_voltage()
        battery_level = witty_pi.input_voltage
    else:
        battery_level = 0.0
        app.logger.warning('Witty Pi not detected')

    sd_card.get_data()

    if sounds_capture_state == 'stopped':

        if microphone:
            microphone.stop()
            microphone = None
            app.logger.info('microphone stopped')

    istopdir = logs_current_directory == LOGS_DESKTOP_FOLDER

    files = sorted(os.listdir(logs_current_directory), reverse=istopdir)

    files = [x for x in files if not x.endswith('.zip')]

    isdirs = [os.path.isdir(os.path.join(logs_current_directory, x)) for x in files]

    return make_response(render_template('logs.html', updates_available=updates_available, files=files, isdirs=isdirs, zip=zip, istopdir=istopdir, show_preview_log=show_preview_log, logs_current_file=logs_current_file, log_data=log_data, rpi=rpi, battery_level=battery_level, sd_card=sd_card))


@app.route('/manage_logs/<action>/<value>')
def manage_logs(action, value):

    global logs_current_directory, logs_current_file, show_preview_log, log_data

    app.logger.info(f'manage_logs() {action} {value}')

    try:

        if action == 'chdir':

            if value == 'up':

                logs_current_directory = '/'.join(logs_current_directory.split('/')[0:-1])

                if not logs_current_directory:
                    logs_current_directory = '/'

                show_preview_log = False
                log_data = None

            else:

                logs_current_directory = os.path.join(logs_current_directory, value)

            logs_current_file = None

        elif action == 'show':

            file_path = os.path.join(logs_current_directory, value)

            logs_current_file = value

            if value.endswith('.log') or '.log.' in value:

                with open(file_path, 'r') as f:
                    log_data = f.read()

                    if not log_data:
                        log_data = 'File empty'
                    elif 'werkzeug' in value:
                        log_data = log_data.replace('[0m','').replace('[1m','').replace('[31m','').replace('[32m','').replace('[33m','').replace('[36m','')

                show_preview_log = True

            else:

                show_preview_log = False

    except BaseException as e:

        app.logger.error(str(e))

    return redirect('/logs')


@app.route('/information')
def information():

    global camera, leds_front, leds_rear_deported_uv, gnss, microphone, logs_current_directory, logs_current_file, show_preview_log, log_data

    get_captures_state()

    if images_capture_state == 'stopped':

        if camera:
            camera.stop()
            camera.camera.close()
            camera = None
            app.logger.info('camera stopped')

        if leds_front:
            leds_front.turn_off()
            leds_front = None
            app.logger.info('LEDs front stopped')

        if leds_rear_deported_uv:
            leds_rear_deported_uv.turn_off()
            leds_rear_deported_uv = None
            app.logger.info('LEDs rear/UV/deported stopped')

    elif images_capture_state == 'paused':

        if leds_front:
            leds_front.turn_off()
            leds_front = None
            app.logger.info('LEDs front stopped')

        if leds_rear_deported_uv:
            leds_rear_deported_uv.turn_off()
            leds_rear_deported_uv = None
            app.logger.info('LEDs rear/UV/deported stopped')

    if gnss:
        gnss.stop()
        gnss = None
        app.logger.info('GNSS stopped')

    gnss = Gnss2()

    # wifi.show()
    # wifi.list()
    # app.logger.info('wifi updated')

    rpi.cpu_temperature = rpi.get_temperature()

    if witty_pi.available:
        witty_pi.get_input_voltage()
        battery_level = witty_pi.input_voltage
    else:
        battery_level = 0.0
        app.logger.warning('Witty Pi not detected')

    sd_card.get_data()

    if sounds_capture_state == 'stopped':

        if microphone:
            microphone.stop()
            microphone = None
            app.logger.info('microphone stopped')

    commit = get_last_commit()

    dateTime.get_date_time_info()

    tzone = datetime.now().astimezone().strftime('%Z')

    dateTime.get_date()
    dateTime.get_time()

    return make_response(render_template('information.html', configuration=configuration, updates_available=updates_available, tzone=tzone, gnss=gnss, wifi=wifi, commit=commit, dateTime=dateTime, zip=zip, rpi=rpi, battery_level=battery_level, sd_card=sd_card))


@app.route('/sounds_capture_test', methods=['POST'])
def sounds_capture_test():

    try:

        duration = request.get_json()

        app.logger.info('json: %s', request.get_json())

        duration = int(duration)

        file_path = ''

        if microphone.available:

            success = microphone.start()

            if success:

                if microphone.stream:

                    app.logger.info('microphone started')

                    now_str = datetime.now().strftime('%Y%m%d%H%M%S')
                    file_path = os.path.join(SOUNDS_CAPTURE_FOLDER, now_str + '_test.wav')

                    total_samples = microphone.sample_rate * duration

                    app.logger.info(f'starting recording {total_samples} samples at {microphone.sample_rate} Hz sample rate during {duration} seconds')

                    data = []
                    while total_samples > 0:

                        samples = min(total_samples, microphone.CHUNK_SIZE)
                        data.append(microphone.stream.read(samples, exception_on_overflow=False))
                        total_samples -= samples

                    app.logger.info('stop recording')

                    microphone.save_recording(file_path, data)

                    app.logger.info('recording saved to ' + file_path)

                microphone.stop()
                app.logger.info('microphone stopped')

                return jsonify(success=True, message='', data=file_path)

            else:

                return jsonify(success=False, message='', data='')

        else:

            return jsonify(success=False, message='', data='')

    except BaseException as e:

        app.logger.error(str(e))

        return jsonify(success=False, message='', data=str(e))


@app.route('/video_feed')
def video_feed():

    if camera and camera.is_camera_supported and camera.started:
        return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return Response('')


def generate_frames():

    global capture_next_image, current_lens_position

    try:

        extra_metadata = {'EntomoscopeSiteID': configuration.site['id'],
                'EntomoscopeLatitude': configuration.gnss['latitude'],
                'EntomoscopeLongitude': configuration.gnss['longitude'],
                'EntomoscopeAltitude': configuration.gnss['altitude'],
                'EntomoscopeLedsFrontIntensity': configuration.leds['intensity_front'],
                'EntomoscopeLedsRearDeportedUvIntensity': configuration.leds['intensity_rear_deported_uv'],
                'EntomoscopeLedsDelayOn': configuration.leds['delay_on'],
                'EntomoscopeLedsDelayOff': configuration.leds['delay_off'],
                'EntomoscopeAiAvailable': AI_AVAILABLE,
                'EntomoscopeAiEnable': configuration.ai_detection['enable'],
                'EntomoscopeAiModel': configuration.ai_detection['file'],
                'EntomoscopeCameraModel': configuration.camera['model'],
                'EntomoscopeFocusMode': configuration.camera['autofocus']['mode'],
                'EntomoscopeRaspberryPiModel': rpi.model,
                'EntomoscopeRaspberryPiMemory': rpi.memory,
                'EntomoscopeRaspberryPiSerialNumber': rpi.serial,
                'EntomoscopeAiPredictionNumBoxes': 0,
                'EntomoscopeAiPredictionSpeed': 0,
                'EntomoscopeAiPredictionBoxes': [],
                'EntomoscopeAiPredictionLabels': [],
                'EntomoscopeAiPredictionConf': [],
                'EntomoscopeAiImageScale': configuration.ai_detection['image_scale'],
                'EntomoscopeAiImageSize': [configuration.ai_detection['image_width'], configuration.ai_detection['image_height']]
                }

    except BaseException as e:

        app.logger.error(str(e))

    time_between_frame = 1 / CAMERA_PREVIEW_FPS

    last_frame_time = time()

    while True:

        if camera and camera.started:

            if not pause_stream and (time() - last_frame_time > time_between_frame):

                last_frame_time = time()

                try:

                    if AI_AVAILABLE and AI_ENABLE and configuration.ai_detection['enable']:

                        # Récupération de la capture image et metadata de la caméra
                        # frame2 : tableau de bytes depuis le stream main
                        # metadata : dictionaire

                        camera.capture()

                        frame2 = camera.frame_data_main
                        metadata = camera.metadata

                        (x,y,w,h) = crop_limits

                    else:

                        # Récupération de la capture image et metadata de la caméra
                        # frame2 : tableau de bytes depuis le stream MJPEG
                        # metadata : dictionaire
                        frame, metadata = camera.get_preview_frame()

                        data = np.frombuffer(frame, dtype=np.uint8)
                        frame2 = cv2.imdecode(data, cv2.IMREAD_COLOR )

                        (x,y,w,h) = crop_limits

                        x = int(x / camera.sensor_resolution[0] * configuration.camera['sensor']['width_preview'])
                        y = int(y / camera.sensor_resolution[1] * configuration.camera['sensor']['height_preview'])
                        w = int(w / camera.sensor_resolution[0] * configuration.camera['sensor']['width_preview'])
                        h = int(h / camera.sensor_resolution[1] * configuration.camera['sensor']['height_preview'])

                    frame2 = frame2[y:y+h,x:x+w,:]

                    if camera.autofocus_available:
                        current_lens_position = metadata['LensPosition']

                    if AI_AVAILABLE and AI_ENABLE and configuration.ai_detection['enable']:

                        # Redimensionnement de l'image pour la détection par IA
                        frameDetect = cv2.resize(frame2, (configuration.ai_detection['image_width'], configuration.ai_detection['image_height']))

                        # Exécution du script IA
                        prediction = ai_model.predict(frameDetect,
                                                        imgsz=(frameDetect.shape[0], frameDetect.shape[1]),
                                                        conf=configuration.ai_detection['min_confidence'],
                                                        show=False,
                                                        save=False,
                                                        save_txt=False,
                                                        verbose=False)[0]

                        # prediction = ai_model.track(frameDetect,
                                                        # imgsz=(frameDetect.shape[0], frameDetect.shape[1]),
                                                        # conf=configuration.ai_detection['min_confidence'],
                                                        # show=False,
                                                        # save=False,
                                                        # save_txt=False,
                                                        # verbose=False)[0]

                        # Arthropode détecté si au moins une boite dans prediction
                        arthropod_detected = len(prediction.boxes) > 0

                        # Si arthropode(s) détecté(s)
                        if arthropod_detected is True:

                            # Vitesse de la détection en millisecondes
                            speed = prediction.speed['preprocess'] + prediction.speed['inference'] + prediction.speed['postprocess']

                            # Nombre de boites détectées
                            num_boxes = len(prediction.boxes)

                            app.logger.info(f'{num_boxes} arthropods detected in {speed:.0f} ms')

                            extra_metadata['EntomoscopeAiPredictionNumBoxes'] = num_boxes
                            extra_metadata['EntomoscopeAiPredictionSpeed'] = f'{speed:.0f}'

                            frame2 = np.ascontiguousarray(frame2)

                            ann = Annotator(
                                frame2,
                                line_width=None,  # default auto-size
                                font_size=None,  # default auto-size
                                font="Arial.ttf",  # must be ImageFont compatible
                                pil=False,  # use PIL, otherwise uses OpenCV
                            )

                            frame3 = copy.copy(frame2)

                            box_xyxy = [0,0,0,0]

                            extra_metadata['EntomoscopeAiPredictionBoxes'].clear()
                            extra_metadata['EntomoscopeAiPredictionConf'].clear()
                            extra_metadata['EntomoscopeAiPredictionLabels'].clear()

                            image_width = frame2.shape[1]
                            image_height = frame2.shape[0]

                            for box in prediction.boxes:

                                box_xyxyn = box.xyxyn.tolist()

                                box_xyxy[0] = box_xyxyn[0][0] * image_width
                                box_xyxy[1] = box_xyxyn[0][1] * image_height
                                box_xyxy[2] = box_xyxyn[0][2] * image_width
                                box_xyxy[3] = box_xyxyn[0][3] * image_height

                                if box.is_track:
                                    label = f'{box.id.item()} {box.conf.item():.2f}'
                                else:
                                    label = f'{box.conf.item():.2f}'

                                ann.box_label(box_xyxy, label, color=colors(0, bgr=True))

                                box_xywhn = box.xywhn.tolist()

                                extra_metadata['EntomoscopeAiPredictionBoxes'].append(box_xywhn[0])
                                extra_metadata['EntomoscopeAiPredictionConf'].append(box.conf.item())
                                if box.is_track:
                                    extra_metadata['EntomoscopeAiPredictionLabels'].append(box.id.item())

                            frame2 = ann.result()

                            text = f'Speed: {speed:.0f} ms'
                            x, y = (0, 0)
                            text_size, _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.25, 2)
                            text_w, text_h = text_size

                            text_w += 10
                            text_h += 15

                            cv2.rectangle(frame2, (x, y), (x + text_w, y + text_h), (0, 0, 0), -1)
                            cv2.putText(frame2, text, (x + 5, y + text_h - 5), cv2.FONT_HERSHEY_SIMPLEX, 1.25, (0, 255, 0), 2)

                            # cv2.putText(frame2, f'Speed: {speed:.0f} ms', (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.25, (0, 0, 255), 2)
                            # cv2.putText(frame2, t, (10, 60 + text_h + 1.25 - 1), cv2.FONT_HERSHEY_SIMPLEX, 1.25, (255, 255, 255), 2)

                            img_encode = cv2.imencode('.jpg', frame2, [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality])[1]

                            if CAPTURE_AI_DETECTION:

                                now_str = datetime.now().strftime('%Y%m%d%H%M%S_%f')

                                img_encode_3 = cv2.imencode('.jpg', frame3, [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality])[1]

                                file_path = os.path.join(IMAGES_CAPTURE_FOLDER, now_str + '_detection_test.jpg')

                                camera.jpeg_data = img_encode_3.tobytes()
                                camera.save_capture(file_path, save_metadata=True, extra_metadata=extra_metadata)

                                # file_path = os.path.join(IMAGES_CAPTURE_FOLDER, now_str + '_detection_test_boxes.jpg')

                                # camera.jpeg_data = img_encode.tobytes()
                                # camera.save_capture(file_path, save_metadata=False)

                            data_encode = np.array(img_encode)
                            frame = data_encode.tobytes()

                        else:

                            img_encode = cv2.imencode('.jpg', frame2, [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality])[1]
                            data_encode = np.array(img_encode)
                            frame = data_encode.tobytes()

                    elif focus_measure_enable:

                        if focus_measure_mode == 'focus_peaking':

                            gray = frame2[..., :3] @ [0.299, 0.587, 0.114]
                            edges = focus.compute_focus(gray, focus_measure_mode)

                            if edges.any():
                                # Apply the red color to in-focus pixels
                                frame2[edges > 0] = [0, 0, 255]

                        else:

                            focus_measure = focus.compute_focus(frame2, focus_measure_mode)

                            text = f'Focus value: {focus_measure:.3f}'
                            x, y = (0, 0)
                            text_size, _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 1.25, 2)
                            text_w, text_h = text_size

                            text_w += 10
                            text_h += 15

                            cv2.rectangle(frame2, (x, y), (x + text_w, y + text_h), (0, 0, 0), -1)
                            cv2.putText(frame2, text, (x + 5, y + text_h - 5), cv2.FONT_HERSHEY_SIMPLEX, 1.25, (0, 255, 0), 2)

                        img_encode = cv2.imencode('.jpg', frame2, [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality])[1]
                        data_encode = np.array(img_encode)
                        frame = data_encode.tobytes()

                    # if capture_next_image:

                        # capture_next_image = False

                        # now_str = datetime.now().strftime('%Y%m%d%H%M%S_%f')

                        # file_path = os.path.join(IMAGES_CAPTURE_FOLDER, now_str)

                        # camera.capture()
                        # camera.frame_to_jpeg(stream='main')

                        # jpeg_file_path, json_file_path = camera.save_capture(file_path + '_capture_test.jpg', save_metadata=False)

                    else:

                        img_encode = cv2.imencode('.jpg', frame2, [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality])[1]
                        data_encode = np.array(img_encode)
                        frame = data_encode.tobytes()

                    try:

                        if frame:

                            yield (b'--frame\r\n'
                                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

                    except RuntimeError as e:

                        app.logger.error(str(e))

                        # break

                except BaseException as e:

                    app.logger.error(str(e))

                    print(traceback.format_exc())

                    # break


@app.route('/manage_images_capture', methods=['POST'])
def manage_images_capture():

    global images_capture_state, sounds_capture_state

    try:

        data = request.get_json()

        app.logger.info('json: %s', request.get_json())

        if data == 'suspend':
            pi.write(IMAGES_CAPTURE_ACTIVITY_PIN, 1)
            images_capture_state = 'paused'
            app.logger.info('imagess capture suspended')
        elif data == 'resume':
            pi.write(IMAGES_CAPTURE_ACTIVITY_PIN, 0)
            images_capture_state = 'running'
            app.logger.info('images capture resumed')
        elif data == 'stop':
            #TODO Pop up ask no yes
            pi.write(SHUTDOWN_PIN, 1)
            sleep(5)
            pi.write(IMAGES_CAPTURE_ACTIVITY_PIN, 1)
            pi.write(SOUNDS_CAPTURE_ACTIVITY_PIN, 1)
            images_capture_state = 'stopped'
            sounds_capture_state = 'stopped'
            app.logger.info('images (and sounds) capture stopped')

        return jsonify(success=True, message='Images capture managed successfully')

    except BaseException as e:

        app.logger.error(str(e))

        return jsonify(success=False, message=str(e))


@app.route('/manage_sounds_capture', methods=['POST'])
def manage_sounds_capture():

    global images_capture_state, sounds_capture_state

    try:

        data = request.get_json()

        app.logger.info('json: %s', request.get_json())

        if data == 'suspend':
            pi.write(SOUNDS_CAPTURE_ACTIVITY_PIN, 1)
            sounds_capture_state = 'paused'
            app.logger.info('sounds capture suspended')
        elif data == 'resume':
            pi.write(SOUNDS_CAPTURE_ACTIVITY_PIN, 0)
            sounds_capture_state = 'running'
            app.logger.info('sounds capture resumed')
        elif data == 'stop':
            #TODO Pop up ask no yes
            pi.write(SHUTDOWN_PIN, 1)
            sleep(5)
            pi.write(IMAGES_CAPTURE_ACTIVITY_PIN, 1)
            pi.write(SOUNDS_CAPTURE_ACTIVITY_PIN, 1)
            images_capture_state = 'stopped'
            sounds_capture_state = 'stopped'
            app.logger.info('sounds (and images) capture stopped')

        return jsonify(success=True, message='Sounds capture managed successfully')

    except BaseException as e:

        app.logger.error(str(e))

        return jsonify(success=False, message=str(e))


@app.route('/save_configuration', methods=['POST'])
def save_configuration():

    try:

        data = request.get_json()

        app.logger.info('json: %s', request.get_json())

        app.logger.info(f'saving {data} in configuration')

        if data == 'camera_model':
            configuration.camera['model'] = camera_model.lower()
            # configuration.camera['sensor']['width_max'] = sensor_resolution[0]
            # configuration.camera['sensor']['height_max'] = sensor_resolution[1]
            configuration.camera['sensor']['preview_mode'] = sensor_mode[0]
            configuration.camera['sensor']['capture_mode'] = sensor_mode[1]
        elif data == 'autofocus':
            configuration.camera['autofocus']['mode'] = autofocus['mode']
            configuration.camera['autofocus']['lens_position'] = autofocus['lens_position']
            configuration.camera['autofocus']['measure_enable'] = focus_measure_enable
            configuration.camera['autofocus']['measure_mode'] = focus_measure_mode
        elif data == 'image_adjustments':
            pass
        elif data == 'auto_exposure_gain':
            configuration.camera['auto_exposure_gain']['exposure_value'] = auto_exposure_gain['exposure_value']
            configuration.camera['auto_exposure_gain']['exposure_time'] = auto_exposure_gain['exposure_time']
            configuration.camera['auto_exposure_gain']['enable'] = auto_exposure_gain['enable']
            if auto_exposure_gain['enable']:
                configuration.camera['auto_exposure_gain']['mode'] = 'Auto'
            else:
                configuration.camera['auto_exposure_gain']['mode'] = 'Manual'
        elif data == 'auto_white_balance':
            configuration.camera['auto_white_balance']['enable'] = white_balance['enable']
            configuration.camera['auto_white_balance']['mode'] = white_balance['mode']
        elif data == 'leds':
            configuration.leds['intensity_front'] = leds_intensity[0]
            configuration.leds['intensity_rear_deported_uv'] = leds_intensity[1]
            configuration.leds['delay_on'] = leds_delays[0]
            configuration.leds['delay_off'] = leds_delays[1]
            configuration.leds['always_on'] = leds_always_on
        elif data == 'files':
            configuration.files['jpeg_quality'] = jpeg_quality
        elif data == 'image_position':
            configuration.camera['sensor']['crop_limits'] = crop_limits
            configuration.camera['image_height'] = crop_limits[3]
            configuration.camera['image_width'] = crop_limits[2]
            configuration.server['image_constraints']['centered'] = server_settings['keep_image_center']
            configuration.server['image_constraints']['square'] = server_settings['keep_image_square']
        elif data == 'ai_detection':
            configuration.ai_detection['enable'] = ai_detection['enable']
            configuration.ai_detection['file'] = ai_detection['file']
            configuration.ai_detection['image_scale'] = ai_detection['image_scale']
            configuration.ai_detection['min_confidence'] = ai_detection['min_confidence']
            configuration.ai_detection['image_width'] = ai_detection['image_width']
            configuration.ai_detection['image_height'] = ai_detection['image_height']

        configuration.save()

        app.logger.info('configuration saved')

        return jsonify(success=True, message='Configuration saved successfully')

    except BaseException as e:

        app.logger.error(str(e))

        return jsonify(success=False, message=str(e))


@app.route('/update_settings', methods=['POST'])
def update_settings():

    try:

        data = request.get_json()

        app.logger.info('json: %s', request.get_json())

        app.logger.info('updating setting ' + data[0])

        if data[0] == 'site':
            configuration.site['id'] = data[1]['id']
            data = None
        elif data[0] == 'capture_mode':
            configuration.mode['mode'] = capture_mode
        elif data[0] == 'images_capture':
            configuration.images_capture['enable'] = data[1]['enable']
            configuration.images_capture['fast_mode'] = data[1]['fast_mode']
            configuration.images_capture['time_step'] = int(data[1]['time_step'])
            configuration.images_capture['multifocus']['enable'] = data[1]['multifocus']
            configuration.images_capture['multifocus']['lens_position_offset'] = float(data[1]['lens_position_offset'])
            data = None
        elif data[0] == 'sounds_capture':
            configuration.sounds_capture['enable'] = data[1]['enable']
            configuration.sounds_capture['duration'] = int(data[1]['duration'])
            data = None
        elif data[0] == 'schedule':
            configuration.schedule['enable'] = data[1]['enable']
            configuration.schedule['on_duration'] = int(data[1]['on_duration'])
            configuration.schedule['off_duration'] = int(data[1]['off_duration'])
            configuration.schedule['periodicity'] = periodicity
            configuration.schedule['next_startup'] = data[1]['startup_date'] + ' ' + data[1]['startup_time']
            configuration.schedule['next_shutdown'] = data[1]['shutdown_date'] + ' ' + data[1]['shutdown_time']

            if configuration.schedule['enable']:

                startup_date = [int(x) for x in configuration.schedule['next_startup'].replace('-', ' ').replace(':', ' ').split()]
                shutdown_date = [int(x) for x in configuration.schedule['next_shutdown'].replace('-', ' ').replace(':', ' ').split()]

                startup_date = datetime(startup_date[0], startup_date[1], startup_date[2], startup_date[3], startup_date[4], 0, 0)
                #startup_date = startup_date.astimezone()

                startup_date = startup_date - timedelta(minutes=MINUTES_OFFSET_FOR_STARTING_ON_TIME)

                if witty_pi.available:
                    # witty_pi.set_startup_alarm(startup_date[2], startup_date[3], startup_date[4])
                    witty_pi.set_startup_alarm(startup_date.day, startup_date.hour, startup_date.minute)
                    witty_pi.set_shutdown_alarm(shutdown_date[2], shutdown_date[3], shutdown_date[4])
                else:
                    app.logger.warning('Witty Pi alarms not set')

        elif data[0] == 'cooling_system':

            configuration.cooling_system['enable'] = data[1]['enable']

            configuration.cooling_system['cpu_temperature_levels'] = [int(x) for x in data[1]['cpu_temps']]
            configuration.cooling_system['fan_speed_levels'] = [int(x) for x in data[1]['fan_speeds']]

            cpu_temperature_check_interval = int(data[1]['cpu_temp_check_interval'])

            configuration.cooling_system['cpu_temperature_check_interval'] = cpu_temperature_check_interval

            if configuration.cooling_system['enable']:
                crontab_management.enable_service('fan_management', cpu_temperature_check_interval)
            else:
                crontab_management.disable_service('fan_management')

        elif data[0] == 'environmental_monitoring':

            configuration.environmental_monitoring['enable'] = data[1]['enable']
            configuration.environmental_monitoring['time_step'] = int(data[1]['time_step'])

            if configuration.environmental_monitoring['enable']:
                crontab_management.enable_service('environmental_monitoring', configuration.environmental_monitoring['time_step'])
            else:
                crontab_management.disable_service('environmental_monitoring')

        configuration.save()

        tzone = datetime.now().astimezone().strftime('%Z')

        app.logger.info('configuration saved')

        return jsonify(success=True, message='Settings updated successfully', data=data, tzone=tzone)

    except BaseException as e:

        app.logger.error(str(e))

        return jsonify(success=False, message=str(e))


@app.route('/update_camera_live_settings', methods=['POST'])
def update_camera_live_settings():

    try:

        data = request.get_json()

        app.logger.info('json: %s', request.get_json())

        success = apply_camera_settings(data[0], data[1])

        return jsonify(success=success, message='Camera live setting set successfully', data=current_lens_position)

    except BaseException as e:

        app.logger.error(str(e))

        return jsonify(success=False, message=str(e))


def apply_camera_settings(settingId, settingValue):

    global crop_limits, pause_stream

    try:

        app.logger.info(f'setting camera control {settingId} to {settingValue}')

        if settingId == 'AfMode':
            autofocus['mode'] = settingValue
            if settingValue == 'Manual':
                settingValue = libcamera.controls.AfModeEnum.Manual
            elif settingValue == 'Auto':
                settingValue = libcamera.controls.AfModeEnum.Auto
            elif settingValue == 'Continuous':
                settingValue = libcamera.controls.AfModeEnum.Continuous
        elif settingId == 'LensPosition':
            autofocus['lens_position'] = settingValue
        elif settingId == 'AwbEnable':
            white_balance['enable'] = settingValue
        elif settingId == 'AwbMode':
            white_balance['mode'] = settingValue
            if settingValue == 'Auto':
                settingValue = libcamera.controls.AwbModeEnum.Auto
            elif settingValue == 'Tungsten':
                settingValue = libcamera.controls.AwbModeEnum.Tungsten
            elif settingValue == 'Fluorescent':
                settingValue = libcamera.controls.AwbModeEnum.Fluorescent
            elif settingValue == 'Indoor':
                settingValue = libcamera.controls.AwbModeEnum.Indoor
            elif settingValue == 'Daylight':
                settingValue = libcamera.controls.AwbModeEnum.Daylight
            elif settingValue == 'Cloudy':
                settingValue = libcamera.controls.AwbModeEnum.Cloudy
        elif settingId == 'ScalerCrop':
            settingValue = [int(x) for x in settingValue]

            crop_limits = settingValue

            # image_width, image_height = camera.get_preview_main_size(settingValue, configuration)

            # camera.camera_config['lores']['size'] = camera.get_preview_lores_size(crop_limits, configuration)

            # app.logger.info(f'camera main size set to ({image_width}, {image_height})')

        elif settingId == 'ExposureValue':
            auto_exposure_gain['exposure_value'] = settingValue
        elif settingId == 'ExposureTime':
            settingValue = int(settingValue)
            auto_exposure_gain['exposure_time'] = settingValue
        elif settingId == 'AeEnable':
            auto_exposure_gain['enable'] = settingValue
            if auto_exposure_gain['enable']:
                 auto_exposure_gain['mode'] = 'Auto'
            else:
                auto_exposure_gain['mode'] = 'Manual'

        if camera:

            pause_stream = True
            sleep(0.1)

            # try:
                # camera.camera.stop_encoder(camera.encoder)
            # except BaseException as e:
                # app.logger.error(str(e))
            # camera.camera.stop()
            # camera.stop()
            # camera.camera.configure(camera.camera_config)

            if settingId == 'LensPosition':
                # camera.camera.set_controls({'AfMode': libcamera.controls.AfModeEnum.Manual, settingId: settingValue})
                camera.set_controls({'AfMode': libcamera.controls.AfModeEnum.Manual, settingId: settingValue})
            elif settingId == 'AfMode' and settingValue == libcamera.controls.AfModeEnum.Manual:
                # camera.camera.set_controls({settingId: settingValue, 'LensPosition': autofocus['lens_position']})
                autofocus['lens_position'] = current_lens_position
                # camera.camera.set_controls({settingId: settingValue, 'LensPosition': current_lens_position})
                camera.set_controls({settingId: settingValue, 'LensPosition': current_lens_position})
            # elif settingId == 'ScalerCrop':
                # # camera.camera.configure(camera.camera_config)
                # # camera.camera.set_controls({settingId: settingValue})
                # camera.set_controls({settingId: settingValue})

                # camera.stop()
                # camera.camera_configure()
                # camera.start()

                # print(camera)
                # metadata = camera.get_metadata()
                # print(metadata)
            # else:
            elif settingId != 'ScalerCrop':
                # camera.camera.set_controls({settingId: settingValue})
                camera.set_controls({settingId: settingValue})

            # try:
                # camera.camera.start_encoder(camera.encoder)
            # except BaseException as e:
                # app.logger.error(str(e))

            # camera.camera.start()
            #camera.start()

            pause_stream = False
            sleep(0.1)

            app.logger.info(f'camera control {settingId} set to {settingValue}')

        success = True

    except BaseException as e:

        app.logger.error(str(e))

        success = False

    return success


@app.route('/set_camera_model', methods=['POST'])
def set_camera_model():

    global camera_model, sensor_resolution, sensor_mode, preview_resolution

    try:

        camera_model = request.get_json()

        app.logger.info('json: %s', request.get_json())

        app.logger.info(f'camera model set to {camera_model}')

        sensor_resolution = camera.get_model_sensor_resolution(camera_model)

        app.logger.info(f'sensor resolution {sensor_resolution[0]}x{sensor_resolution[1]} pixels')

        preview_resolution = camera.get_model_preview_resolution(camera_model)

        app.logger.info(f'preview resolution {preview_resolution[0]}x{preview_resolution[1]} pixels')

        sensor_mode = camera.get_sensor_mode(camera_model)

        # autofocus_available = camera.get_autofocus_available(camera_model)

        return jsonify(success=True, message='Camera model set successfully', sensor_resolution=sensor_resolution)

    except BaseException as e:

        app.logger.error(str(e))

        return jsonify(success=False, message=str(e))

@app.route('/set_focus_measure_enable', methods=['POST'])
def set_focus_measure_enable():

    global focus_measure_enable

    try:

        focus_measure_enable = request.get_json()

        app.logger.info('json: %s', request.get_json())

        app.logger.info(f'focus measure enable set to {focus_measure_enable}')

        return jsonify(success=True, message='Focus measure enable set successfully')

    except BaseException as e:

        app.logger.error(str(e))

        return jsonify(success=False, message=str(e))



@app.route('/set_focus_measure_mode', methods=['POST'])
def set_focus_measure_mode():

    global focus_measure_mode

    try:

        focus_measure_mode = request.get_json()

        app.logger.info('json: %s', request.get_json())

        app.logger.info(f'focus measure mode set to {focus_measure_mode}')

        return jsonify(success=True, message='Focus measure mode set successfully')

    except BaseException as e:

        app.logger.error(str(e))

        return jsonify(success=False, message=str(e))

@app.route('/set_capture_mode', methods=['POST'])
def set_capture_mode():

    global capture_mode

    try:

        capture_mode = request.get_json()

        app.logger.info('json: %s', request.get_json())

        app.logger.info(f'images capture mode set to {capture_mode}')

        return jsonify(success=True, message='Images capture mode set successfully')

    except BaseException as e:

        app.logger.error(str(e))

        return jsonify(success=False, message=str(e))


@app.route('/set_leds_delay', methods=['POST'])
def set_leds_delay():

    global leds_delays

    try:

        data = request.get_json()

        app.logger.info('json: %s', request.get_json())

        if data[0] == 'on':
            leds_delays[0] = float(data[1])
        elif data[0] == 'off':
            leds_delays[1] = float(data[1])

        app.logger.info(f'LEDs delay {data[0]} set to {data[1]} seconds')

        return jsonify(success=True, message='LEDs delay set successfully')

    except BaseException as e:

        app.logger.error(str(e))

        return jsonify(success=False, message=str(e))


@app.route('/set_leds_always_on', methods=['POST'])
def set_leds_always_on():

    global leds_always_on, leds_delays

    try:

        data = request.get_json()

        app.logger.info('json: %s', request.get_json())

        leds_always_on = data

        if leds_always_on:
            leds_delays = [0, 0]
        else:
            leds_delays = [configuration.leds['delay_on'], configuration.leds['delay_off']]

        app.logger.info(f'LEDs always on set to {data}')

        data = leds_delays

        return jsonify(success=True, message='LEDs always on set successfully', data=data)

    except BaseException as e:

        app.logger.error(str(e))

        return jsonify(success=False, message=str(e))


@app.route('/update_leds_live_settings', methods=['POST'])
def update_leds_live_settings():

    try:

        data = request.get_json()

        app.logger.info('json: %s', request.get_json())

        if data[0] == 'intensity_front':
            leds_front.set_intensity(data[1])
            leds_front.turn_on()
            leds_intensity[0] = data[1]
            app.logger.info(f'LEDs front intenstiy set to {data[1]} %')
        elif data[0] == 'intensity_rear_deported_uv':
            leds_rear_deported_uv.set_intensity(data[1])
            leds_rear_deported_uv.turn_on()
            leds_intensity[1] = data[1]
            app.logger.info(f'LEDs Rear/Deported/UV intenstiy set to {data[1]} %')

        return jsonify(success=True, message='LEDs live setting set successfully')

    except BaseException as e:

        app.logger.error(str(e))

        return jsonify(success=False, message=str(e))


@app.route('/move_image', methods=['POST'])
def move_image():

    global crop_limits

    try:

        data = request.get_json()

        app.logger.info('json: %s', request.get_json())

        # print(data, flush=True)

        if data[0] == 'up':

            crop_limits[1] -= int(data[1])
            if crop_limits[1] < 0:
                crop_limits[1] = 0

        elif data[0] == 'down':

            crop_limits[1] += int(data[1])

        elif data[0] == 'left':

            crop_limits[0] -= int(data[1])
            if crop_limits[0] < 0:
                crop_limits[0] = 0

        elif data[0] == 'right':

            crop_limits[0] += int(data[1])

        if camera and camera.started:
            # camera.set_controls({'ScalerCrop': crop_limits})
            app.logger.info(f'image moved to {crop_limits}')

        return jsonify(success=True, message="Image moved successfully", crop_limits=crop_limits)

    except BaseException as e:

        app.logger.error(str(e))

        return jsonify(success=False, message=str(e))


@app.route('/set_server_settings', methods=['POST'])
def set_server_settings():

    global server_settings

    try:

        data = request.get_json()

        app.logger.info('json: %s', request.get_json())

        if data[0] == 'keep_center':
            server_settings['keep_image_center'] = data[1]
        elif data[0] == 'keep_square':
            server_settings['keep_image_square'] = data[1]

        app.logger.info(f'server setting {data[0]} set to {data[1]}')

        return jsonify(success=True, message="Settings updated successfully")

    except BaseException as e:

        app.logger.error(str(e))

        return jsonify(success=False, message=str(e))


@app.route('/set_detection_scale', methods=['POST'])
def set_detection_scale():

    global ai_detection, camera

    try:

        data = request.get_json()

        app.logger.info('json: %s', request.get_json())

        ai_detection['image_scale'] = int(data[0])
        ai_detection['image_width'] = int(data[1])
        ai_detection['image_height'] = int(data[2])

        # lores_size = (int(data[1]), int(data[2]))

        # camera.camera_config['lores']['size'] = lores_size

        # # camera.camera.stop_encoder(camera.encoder)
        # camera.camera.stop()
        # camera.camera.configure(camera.camera_config)
        # # camera.camera.start_encoder(camera.encoder)
        # camera.camera.start()

        # app.logger.info(f'camera lores size set to ({lores_size[0]}, {lores_size[1]})')

        return jsonify(success=True, message="Settings updated successfully")

    except BaseException as e:

        app.logger.error(str(e))

        return jsonify(success=False, message=str(e))


@app.route('/set_detection_enable', methods=['POST'])
def set_detection_enable():

    global ai_detection

    try:

        data = request.get_json()

        app.logger.info('json: %s', request.get_json())

        ai_detection['enable'] = data

        app.logger.info(f"ai detection set to {ai_detection['enable']}")

        return jsonify(success=True, message="Settings updated successfully")

    except BaseException as e:

        app.logger.error(str(e))

        return jsonify(success=False, message=str(e))


@app.route('/set_ai_model_file', methods=['POST'])
def set_ai_model_file():

    global ai_detection, ai_model

    try:

        data = request.get_json()

        app.logger.info('json: %s', request.get_json())

        ai_detection['file'] = data

        ai_model_file = os.path.join(AI_MODEL_PATH, ai_detection['file'])
        start_time = datetime.now()
        ai_model = YOLO(ai_model_file)
        elapsed_time = datetime.now() - start_time
        app.logger.info(f"AI model file loaded: {ai_detection['file']}")
        app.logger.info(f"AI model file loading time: {elapsed_time.seconds}.{elapsed_time.microseconds} seconds")

        return jsonify(success=True, message="Settings updated successfully")

    except BaseException as e:

        app.logger.error(str(e))

        return jsonify(success=False, message=str(e))


@app.route('/set_detection_min_confidence', methods=['POST'])
def set_detection_min_confidence():

    global ai_detection

    try:

        data = request.get_json()

        app.logger.info('json: %s', request.get_json())

        ai_detection['min_confidence'] = float(data)

        app.logger.info(f"ai minimal confidence set to {ai_detection['min_confidence']}")

        return jsonify(success=True, message="Settings updated successfully")

    except BaseException as e:

        app.logger.error(str(e))

        return jsonify(success=False, message=str(e))


@app.route('/capture_image', methods=['POST'])
def capture_image():

    global capture_next_image

    try:

        capture_next_image = True

        return jsonify(success=True, message="Settings updated successfully")

    except BaseException as e:

        app.logger.error(str(e))

        return jsonify(success=False, message=str(e))


@app.route('/set_jpeg_quality', methods=['POST'])
def set_jpeg_quality():

    global jpeg_quality

    try:

        jpeg_quality = request.get_json()

        app.logger.info('json: %s', request.get_json())

        jpeg_quality = int(jpeg_quality)

        if camera:
            camera.set_encode_parameter(jpeg_quality)

        app.logger.info(f'JPEG quality set to {jpeg_quality} %')

        return jsonify(success=True, message="Settings updated successfully")

    except BaseException as e:

        app.logger.error(str(e))

        return jsonify(success=False, message=str(e))


@app.route('/set_periodicity', methods=['POST'])
def set_periodicity():

    global periodicity

    try:

        periodicity = request.get_json()

        app.logger.info('json: %s', request.get_json())

        app.logger.info(f'schedule periodicity set to {periodicity}')

        return jsonify(success=True, message="Settings updated successfully")

    except BaseException as e:

        app.logger.error(str(e))

        return jsonify(success=False, message=str(e))

@app.route('/save_microphone_settings', methods=['POST'])
def save_microphone_settings():

    try:

        data = request.get_json()

        app.logger.info('json: %s', request.get_json())

        configuration.microphone['sample_rate'] = data[0]
        configuration.microphone['gain'] = data[1]

        configuration.save()

        app.logger.info(f"configuration for microphone sample rate ({configuration.microphone['sample_rate']}) saved")
        app.logger.info(f"configuration for microphone gain ({configuration.microphone['gain']}) saved")

        if microphone and microphone.available:

            microphone.set_settings(configuration.microphone['sample_rate'], configuration.microphone['gain'])
            microphone.detect_microphone()

        return jsonify(success=True, message='Microphone settings saved successfully', data=data)

    except BaseException as e:

        app.logger.error(str(e))

        return jsonify(success=False, message=str(e))


@app.route('/get_gnss_data', methods=['POST'])
def get_gnss_data():

    try:

        gnss.start()

        sleep(0.1)

        gnss.get_data(2, False)

        gnss.stop()

        app.logger.info('GNSS data get')

        return jsonify(success=True, message='GNSS data get successfully', data=gnss.data)

    except BaseException as e:

        app.logger.error(str(e))

        return jsonify(success=False, message=str(e))


@app.route('/gnss_sync_time', methods=['POST'])
def gnss_sync_time():

    try:

        gnss.start()

        gnss.get_data(2)

        gnss.stop()

        if gnss.data_ready:

            dateTime.set_time_utc(gnss.data['date'][0], gnss.data['date'][1], gnss.data['date'][2], gnss.data['time'][0], gnss.data['time'][1], gnss.data['time'][2])

            dateTime.get_date_time_info()

            app.logger.info('Raspberry Pi time synchronized with GNSS time')

            now = datetime.now()

            if witty_pi.available:
                witty_pi.set_date(now.year, now.month, now.day, now.hour, now.minute, now.second)
            else:
                app.logger.warning('Witty Pi clock not synchronized')

            return jsonify(success=True, message='RPi time synchronized with GNSS successfully', date_time_info=dateTime.date_time_info)

        else:

            app.logger.info('Raspberry Pi time not synchronized with GNSS time => data not ready')

            return jsonify(success=False, message='RPi time not synchronized with GNSS')

    except BaseException as e:

        app.logger.error(str(e))

        return jsonify(success=False, message=str(e))


@app.route('/save_gnss_position', methods=['POST'])
def save_gnss_position():

    try:

        latitude, ns, longitude, ew, altitude, last_update, satellites_used = gnss.get_position()

        # https://tuto-carto.fr/cartographie-generale/theorie-cartographie/longitude-latitude-precision/
        # Nombre de chiffres apres la virgule 	Decimale 	Equivalent en metres 	Interpretation
        # 0 	1.0 	111.32 km 	Pays
        # 1 	0.1 	11.132 km 	Grande ville
        # 2 	0.01 	1.1132 km 	Village
        # 3 	0.001 	111.32 m 	Rue
        # 4 	0.0001 	11.132 m 	Champ
        # 5 	0.00001 	1.1132 m 	Arbre
        # 6 	0.000001 	111.32 mm 	Humain
        # 7 	0.0000001 	11.132 mm 	Limite des instruments GPS commerciaux
        # 8 	0.00000001 	1.1132 mm 	Tectonique des plaques

        configuration.gnss['latitude'] = f'{latitude:.6f} {ns}'
        configuration.gnss['longitude'] = f'{longitude:.6f} {ew}'
        configuration.gnss['altitude'] = altitude
        configuration.gnss['last_update'] = last_update
        configuration.gnss['satellites_used'] = satellites_used

        configuration.save()

        app.logger.info('GNSS position saved')

        return jsonify(success=True, message='GNSS position saved successfully', data=[latitude, ns, longitude, ew, altitude, satellites_used])

    except BaseException as e:

        app.logger.error(str(e))

        return jsonify(success=False, message=str(e))


@app.route('/set_date', methods=['POST'])
def set_date():

    try:

        data = request.get_json()

        app.logger.info('json: %s', request.get_json())

        dateTime.set_date_time_2(data[0], data[1])

        dateTime.get_date_time_info()

        date = [int(x) for x in data[0].split('-')]
        time = [int(x) for x in data[1].split(':')]

        if witty_pi.available:

            witty_pi.set_date(date[0], date[1], date[2], time[0], time[1], time[2])

            return jsonify(success=True, message='Date set successfully', data=dateTime.date_time_info)

        else:

            app.logger.warning('Witty Pi clock not set')

            return jsonify(success=False, message='Witty Pi not detected')

    except BaseException as e:

        app.logger.error(str(e))

        return jsonify(success=False, message=str(e))


@app.route('/get_lepinoc_ephemeris', methods=['POST'])
def get_lepinoc_ephemeris():

    try:

        ephemeris = Ephemeris()

        if ephemeris.file_found:

            if ephemeris.today_setting['str']:

                next_startup = datetime(TODAY_NOW.year, TODAY_NOW.month, TODAY_NOW.day, ephemeris.today_setting['hour'], ephemeris.today_setting['minute'], 0, 0, tzinfo=timezone.utc)
                next_shutdown = next_startup + timedelta(hours=4) + timedelta(minutes=5)

                next_startup = next_startup.astimezone()
                next_shutdown = next_shutdown.astimezone()

                next_startup = [next_startup.strftime('%Y-%m-%d'), next_startup.strftime('%H:%M')]
                next_shutdown = [next_shutdown.strftime('%Y-%m-%d'), next_shutdown.strftime('%H:%M')]

        return jsonify(success=True, message='CPU temperature read successfully', next_startup=next_startup, next_shutdown=next_shutdown)

    except Exception as e:

        app.logger.error('' + str(e))

        return jsonify(success=False, message=str(e))


@app.route('/add_wifi', methods=['POST'])
def add_wifi():

    global wifi

    data = request.get_json()

    if data[1]:

        success = wifi.add(data[0], data[1])

        if success:
            app.logger.info(f'wifi {data[0]} added')
        else:
            app.logger.error(f'wifi {data[0]} not added')

    return redirect('/')


# @app.route('/rename_wifi_ap', methods=['POST'])
# def rename_wifi_ap():

    # global wifi

    # name = request.get_json()

    # success = wifi.

    # if success:
        # app.logger.info(f'Wifi {name} removed')
    # else:
        # app.logger.error(f'Wifi {name} not removed')

    # return redirect('/')


@app.route('/remove_wifi', methods=['POST'])
def remove_wifi():

    global wifi

    name = request.get_json()

    success = wifi.remove(name)

    if success:
        app.logger.info(f'wifi {name} removed')

        if configuration.wifi['station_ssid'] == name:
            configuration.wifi['station_ssid'] = ''
            configuration.save()

            app.logger.info(f'wifi {name} removed from configuration file')

    else:
        app.logger.error(f'wifi {name} not removed')

    return redirect('/')


@app.route('/set_wifi', methods=['POST'])
def set_wifi():

    name = request.get_json()

    configuration.wifi['station_ssid'] = name
    configuration.save()

    app.logger.info(f'wifi set to {name}')
    app.logger.info('configuration saved')

    return redirect('/')


@app.route('/refresh_wifi', methods=['POST'])
def refresh_wifi():

    wifi.show()
    wifi.list()

    app.logger.info(f'wifi connections refreshed')

    return redirect('/')


@app.route('/test_internet_connection', methods=['POST'])
def test_internet_connection():

    try:

        success = wifi.test_internet_connection()

        return jsonify(success=success)

    except Exception as e:

        app.logger.error('' + str(e))

        return jsonify(success=False, message=str(e))


@app.route('/get_cpu_temperature', methods=['POST'])
def get_cpu_temperature():

    try:

        return jsonify(success=True, message='CPU temperature read successfully', temperature=rpi.get_temperature())

    except Exception as e:

        app.logger.error('' + str(e))

        return jsonify(success=False, message=str(e))

@app.route('/get_battery_level', methods=['POST'])
def get_battery_level():

    try:

        if witty_pi.available:
            witty_pi.get_input_voltage()
            battery_level = witty_pi.input_voltage
        else:
            battery_level = 0.0
            app.logger.warning('Witty Pi not detected')

        return jsonify(success=True, message='Battery level read successfully', battery_level=battery_level)

    except Exception as e:

        app.logger.error('' + str(e))

        return jsonify(success=False, message=str(e))

@app.route('/get_sd_card_usage', methods=['POST'])
def get_sd_card_usage():

    try:

        sd_card.get_data()

        return jsonify(success=True, message='SD card usage read successfully', sd_card_usage=sd_card.used_percent_num)

    except Exception as e:

        app.logger.error('' + str(e))

        return jsonify(success=False, message=str(e))

@app.route('/check_updates', methods=['POST'])
def check_updates():

    global updates_available

    try:

        updates_available = updates_check()
        app.logger.info(f'updates available? {updates_available}')

        return jsonify(success=True, message='Updates check successfully', updates_available=updates_available)

    except Exception as e:

        app.logger.error('' + str(e))

        return jsonify(success=False, message=str(e), updates_available=updates_available)

@app.route('/download_updates', methods=['POST'])
def download_updates():

    global updates_available

    if updates_available:

        try:

            updates_done = updates_get()
            app.logger.info(f'updates done? {updates_done}')

            updates_available = False

            return jsonify(success=True, message='Updates done successfully', updates_done=updates_done)

        except Exception as e:

            app.logger.error('' + str(e))

            return jsonify(success=False, message=str(e), updates_done=False)

    else:

        return redirect('/')

@app.route('/reboot', methods=['POST'])
def reboot():

    try:

        os.system('python ' + os.path.join(PYTHON_SCRIPTS_BASE_FOLDER, 'shutdown.py'))
        os.system('sudo shutdown -r now')

        return jsonify(success=True, message='Success')

    except Exception as e:

        app.logger.error('' + str(e))

        return jsonify(success=False, message=str(e), updates_done=False)

@app.route('/shutdown', methods=['POST'])
def shutdown():

    try:

        os.system('python ' + os.path.join(PYTHON_SCRIPTS_BASE_FOLDER, 'shutdown.py'))
        os.system('sudo shutdown now')

        return jsonify(success=True, message='Success')

    except Exception as e:

        app.logger.error('' + str(e))

        return jsonify(success=False, message=str(e), updates_done=False)


@app.route('/eject_external_drive', methods=['POST'])
def eject_external_drive():

    try:

        external_disk.eject()

        return jsonify(success=True, message='Success')

    except Exception as e:

        app.logger.error('' + str(e))

        return jsonify(success=False, message=str(e), updates_done=False)

# @app.after_request
# def add_header(response):
    # response.cache_control.max_age = 5
    # return response

@app.before_request
def log_request_info():
    if not request.path.startswith('/static/') and not request.path.startswith('/get_cpu_temperature'):
        app.logger.info('route to %s', request.path)
    #app.logger.info('Headers: %s', request.headers)
    #app.logger.info('Body: %s', request.get_data())

@app.errorhandler(500)
def server_error(error):

    app.logger.error('an exception occurred during a request.')

    if witty_pi.available:
        witty_pi.get_input_voltage()
        battery_level = witty_pi.input_voltage
    else:
        battery_level = 0.0
        app.logger.warning('Witty Pi not detected')

    sd_card.get_data()

    rpi.cpu_temperature = rpi.get_temperature()

    return render_template('500.html', rpi=rpi, battery_level=battery_level, sd_card=sd_card), 500

@app.errorhandler(404)
def page_not_found(error):

    app.logger.error(error)

    if witty_pi.available:
        witty_pi.get_input_voltage()
        battery_level = witty_pi.input_voltage
    else:
        battery_level = 0.0
        app.logger.warning('Witty Pi not detected')

    sd_card.get_data()

    rpi.cpu_temperature = rpi.get_temperature()

    return render_template('404.html', rpi=rpi, battery_level=battery_level, sd_card=sd_card), 404

@app.errorhandler(400)
def file_not_found(error):

    app.logger.error(error)

    if witty_pi.available:
        witty_pi.get_input_voltage()
        battery_level = witty_pi.input_voltage
    else:
        battery_level = 0.0
        app.logger.warning('Witty Pi not detected')

    sd_card.get_data()

    rpi.cpu_temperature = rpi.get_temperature()

    return render_template('400.html', rpi=rpi, battery_level=battery_level, sd_card=sd_card)

def get_data_folders_stats():

    stats = {'folders': [],
            'stat': [],
            'total': {'num_sounds_files': 0,
            'size_sounds_files': 0,
            'num_images_files': 0,
            'size_images_files': 0,
            'num_timelapse_files': 0,
            'num_detection_files': 0,
            'num_test_detection_files': 0,
            'size_all_files': 0}}

    try:

        folder_content = sorted(os.listdir(DATA_FOLDER), reverse=True)

        stats['folders'] = [x for x in folder_content if os.path.isdir(os.path.join(DATA_FOLDER, x))]

        for folder in stats['folders']:

            stat = {'num_sounds_files': 0,
                    'size_sounds_files': 0,
                    'num_images_files': 0,
                    'size_images_files': 0,
                    'num_timelapse_files': 0,
                    'num_detection_files': 0,
                    'num_test_detection_files': 0,
                    'size_all_files': 0}

            sounds_files = [x for x in os.listdir(os.path.join(DATA_FOLDER, folder, 'Sounds')) if x.endswith('.wav')]
            stat['num_sounds_files'] = len(sounds_files)
            stats['total']['num_sounds_files'] += stat['num_sounds_files']
            size = 0
            for sounds_file in sounds_files:
                size += os.path.getsize(os.path.join(DATA_FOLDER, folder, 'Sounds', sounds_file))
            stat['size_sounds_files'] = int(size / 1024 // 1024)
            stats['total']['size_sounds_files'] += stat['size_sounds_files']

            images_files = [x for x in os.listdir(os.path.join(DATA_FOLDER, folder, 'Images')) if x.endswith('.jpg')]
            stat['num_images_files'] = len(images_files)
            stats['total']['num_images_files'] += stat['num_images_files']
            size = 0
            for images_file in images_files:
                size += os.path.getsize(os.path.join(DATA_FOLDER, folder, 'Images', images_file))
            stat['size_images_files'] = int(size / 1024 // 1024)
            stats['total']['size_images_files'] += stat['size_images_files']

            timelapse_files = [x for x in os.listdir(os.path.join(DATA_FOLDER, folder, 'Images')) if x.endswith('_timelapse_no_ai.jpg')]
            stat['num_timelapse_files'] = len(timelapse_files)
            stats['total']['num_timelapse_files'] += stat['num_timelapse_files']

            detection_files = [x for x in os.listdir(os.path.join(DATA_FOLDER, folder, 'Images')) if x.endswith('.jpg') and len(x) == 18]
            stat['num_detection_files'] = len(detection_files)
            stats['total']['num_detection_files'] += stat['num_detection_files']

            test_detection_files = [x for x in os.listdir(os.path.join(DATA_FOLDER, folder, 'Images')) if x.endswith('_detection_test.jpg')]
            stat['num_test_detection_files'] = len(test_detection_files)
            stats['total']['num_test_detection_files'] += stat['num_test_detection_files']

            stat['size_all_files'] = stat['size_sounds_files'] + stat['size_images_files']

            stats['total']['size_all_files'] += stat['size_all_files']

            stats['stat'].append(stat)

    except BaseException as e:

        app.logger.error(str(e))

    # print(stats)

    return stats


def get_captures_state():

    global images_capture_state, sounds_capture_state

    if pi.read(SHUTDOWN_PIN) == 1:

        images_capture_state = 'stopped'
        sounds_capture_state = 'stopped'

    else:

        if pi.read(IMAGES_CAPTURE_ACTIVITY_PIN) == 0:
            images_capture_state = 'running'
        else:
            images_capture_state = 'paused'

        if pi.read(SOUNDS_CAPTURE_ACTIVITY_PIN) == 0:
            sounds_capture_state = 'running'
        else:
            sounds_capture_state = 'paused'

# @socketio.on('connect')
# def handle_connect():
    # """Called when a client connects"""
    # # app.logger.info('client connected')
    # print('client connected')


# @socketio.on('disconnect')
# def handle_disconnect():
    # """Called when a client disconnects"""
    # # app.logger.info('client disconnected')
    # print('client disconnected')

# @socketio.on_error()
# def handle_error(e):
    # """Global error handler for the default namespace"""
    # app.logger.error(f"socketIO: {e}")
    # # Optionally notify the client
    # socketio.emit('error', {'message': 'An error occurred'})

if __name__ == '__main__':

    # socketio.run(app, host='0.0.0.0', debug=SERVER_DEBUG, port=SERVER_PORT)

    app.run(host='0.0.0.0', debug=SERVER_DEBUG, port=SERVER_PORT)

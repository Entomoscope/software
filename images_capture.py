import os
from time import time, sleep
from datetime import datetime

import logging

import pigpio

pi = pigpio.pi()

from configuration import Configuration

from peripherals.camera import Camera
from peripherals.leds import Leds
from peripherals.laser import Laser
from peripherals.pinout import IMAGES_CAPTURE_ACTIVITY_PIN, SHUTDOWN_PIN, LEDS_REAR_PIN, LEDS_FRONT_PIN, LEDS_UV_PIN, LEDS_DEPORTED_PIN
from peripherals.rpi import Rpi

from globals_parameters import IMAGES_CAPTURE_FOLDER, AI_MODEL, LOGS_FOLDER, TODAY

rpi = Rpi()
if rpi.os_version == '64-bit':
    AI_AVAILABLE = True
    from ultralytics import YOLO
else:
    AI_AVAILABLE = False

# Mode 1: Trap => LEDs Rear + LEDs Front
# Mode 2: Lepinoc => LEDs Front + LEDs UV
# Mode 3: Deported camera => LEDs Deported

this_script = os.path.basename(__file__)[:-3]

def isSignalToShutdownReceived():

    return pi.read(SHUTDOWN_PIN)

def isSignalToStandByReceived():

    return pi.read(IMAGES_CAPTURE_ACTIVITY_PIN)

def main():

    logger = logging.getLogger('main')
    filename = os.path.join(LOGS_FOLDER, TODAY + '_' + this_script + '.log')
    logging.basicConfig(filename=filename,
                        format='%(asctime)s;%(levelname)s;"%(message)s"',
                        encoding='utf-8',
                        datefmt='%d/%m/%Y;%H:%M:%S',
                        level=logging.DEBUG)

    logger.info(f'{this_script}: in standby mode. Wait for resume signal to start')

    while isSignalToStandByReceived():

        if isSignalToShutdownReceived():
            logger.info(f'{this_script}: shutdown signal received')
            logger.info(f'{this_script}: stop')
            exit()

        sleep(0.5)

    logger.info(f'{this_script}: resume signal received')

    configuration = Configuration()
    logger.info(f'{this_script}: configuration file read')

    logger.info(f"{this_script}: capturing images using mode {configuration.leds['mode']}")
    logger.info(f"{this_script}: capturing images using time step of {configuration.images_capture['time_step']} seconds")

    leds_rear = Leds(LEDS_REAR_PIN)
    leds_front = Leds(LEDS_FRONT_PIN)
    leds_uv = Leds(LEDS_UV_PIN)
    leds_deported = Leds(LEDS_DEPORTED_PIN)

    if configuration.leds['mode'] == 1:
        leds_rear.set_intensity(configuration.leds['intensity_rear'])
        logger.info(f'{this_script}: LEDs rear set')
    if configuration.leds['mode'] == 1 or configuration.leds['mode'] == 2:
        leds_front.set_intensity(configuration.leds['intensity_front'])
        logger.info(f'{this_script}: LEDs front set')
    if configuration.leds['mode'] == 2:
        leds_uv.set_intensity(configuration.leds['intensity_uv'])
        logger.info(f'{this_script}: LEDs uv set')
    if configuration.leds['mode'] == 3:
        leds_deported.set_intensity(configuration.leds['intensity_deported'])
        logger.info(f'{this_script}: LEDs deported set')

    if AI_AVAILABLE:

        if configuration.ai_detection['enable']:

            logger.info(f'{this_script}: AI detection enabled')

            ai_model = YOLO(AI_MODEL) # load .pt file

            logger.info(f'{this_script}: YOLO ai_model loaded => {AI_MODEL}')
            logger.info(f"{this_script}: detection using images of size {configuration.ai_detection['image_width']}x{configuration.ai_detection['image_height']}")
            logger.info(f"{this_script}: detection using minimal confidence of {configuration.ai_detection['min_confidence']}")

        else:

            ai_model = None
            logger.info(f'{this_script}: AI detection disabled')
    else:
            logger.info(f'{this_script}: AI not available on 32-bit system')

    if configuration.laser['enable']:
        laser = Laser()
    else:
        laser = None

    try:

        camera = Camera(configuration=configuration)

    except BaseException as e:

        logger.error(f'{this_script}: something bad happended with the camera. Read below.')
        logger.error(f'{this_script}: ' + str(e))
        logger.info(f'{this_script}: stop')
        exit()

    if camera.camera is None:
        logger.error(f'{this_script}: camera not found')
        logger.info(f'{this_script}: stop')
        exit()

    if not camera.configured:
        logger.error(f'{this_script}: camera not configured')
        logger.info(f'{this_script}: stop')
        exit()

    camera.start()
    logger.info(f'{this_script}: camera started')

    logger.info(f'{this_script}: start capturing images')

    if configuration.leds['mode'] == 2:
        leds_uv.turn_on()

    shutdown_signal_received = False

    on_duration = configuration.schedule['on_duration'] * 60
    off_duration = configuration.schedule['off_duration'] * 60

    logger.info(f"{this_script}: on duration: {configuration.schedule['on_duration']} minutes")
    logger.info(f"{this_script}: off duration: {configuration.schedule['off_duration']} minutes")

    on = True
    off = not(on)

    if on:
        logger.info(f'{this_script}: on')

    previous_on_time = time()
    previous_off_time = time()
    previous_capture_time = 0

    extra_metadata = {'SiteID': configuration.site['id'], 'Latitude': configuration.gnss['latitude'], 'Longitude': configuration.gnss['longitude']}

    while True:

        if on and (time() - previous_on_time > on_duration):

            previous_off_time = time()
            on = False
            off = True
            logger.info(f'{this_script}: off')

        if off and (time() - previous_off_time > off_duration):

            previous_on_time = time()
            previous_capture_time = 0
            on = True
            off = False
            logger.info(f'{this_script}: on')

        if on and (time() - previous_capture_time > configuration.images_capture['time_step']):

            previous_capture_time = time()

            now_str = datetime.now().strftime('%Y%m%d%H%M%S')

            file_path = os.path.join(IMAGES_CAPTURE_FOLDER, now_str)

            if configuration.leds['mode'] == 1:
                leds_rear.turn_on()
            if configuration.leds['mode'] == 1 or configuration.leds['mode'] == 2:
                leds_front.turn_on()
            if configuration.leds['mode'] == 3:
                leds_deported.turn_on()
                
            if configuration.leds['delay_on']:                
                sleep(configuration.leds['delay_on'])

            camera.capture(get_metadata=True)
            
            if configuration.leds['delay_off']:                
                sleep(configuration.leds['delay_off'])

            if configuration.leds['mode'] == 1:
                leds_rear.turn_off()
            if configuration.leds['mode'] == 1 or configuration.leds['mode'] == 2:
                leds_front.turn_off()
            if configuration.leds['mode'] == 3:
                leds_deported.turn_off()

            # If RPi capable of AI => store image only if insects
            if AI_AVAILABLE and configuration.ai_detection['enable']:

                prediction = ai_model.predict(camera.frame_data_lores, imgsz=(configuration.ai_detection['image_width'], configuration.ai_detection['image_height']), conf=configuration.ai_detection['min_confidence'], show=False, save=False, save_txt=False, verbose=False)[0]

                insect_detected = len(prediction.boxes) > 0

                if insect_detected is True:

                    prediction.save_txt(file_path + '_boxes_conf.txt', save_conf=True)
                    prediction.save(file_path + '_boxes_conf.jpg')

                    camera.frame_to_jpeg(stream='main')

                    jpeg_file_path, json_file_path = camera.save_capture(file_path + '_original.jpg', save_metadata=True, extra_metadata=extra_metadata)

                    box_num = 0;

                    for box in prediction.boxes:
                        box_lists = box.xywhn.tolist()
                        for box_list in box_lists:
                            x, y, w, h = int(box_list[0] * configuration.camera['image_width']), int(box_list[1] * configuration.camera['image_height']), int(box_list[2] * configuration.camera['image_width']), int(box_list[3] * configuration.camera['image_height'])
                            camera.frame_to_jpeg(stream='main', crop=[int(y-h/2),int(y+h/2),int(x-w/2),int(x+w/2)])
                            box_num += 1
                            camera.save_jpeg(file_path + f'_box_{box_num}.jpg')

            # If laser => store image only if insects is detected by the laser
            elif laser and laser.detect_something():

                camera.frame_to_jpeg(stream='main')

                jpeg_file_path, json_file_path = camera.save_capture(file_path + '_original.jpg', save_metadata=True, extra_metadata=extra_metadata)

            # No AI and no laser = store every image
            else:

                camera.frame_to_jpeg(stream='main')

                jpeg_file_path, json_file_path = camera.save_capture(file_path + '_no_detection.jpg', save_metadata=True, extra_metadata=extra_metadata)

        if isSignalToStandByReceived():

            logger.info(f'{this_script}: in standby mode. Wait for signal to resume')

            while isSignalToStandByReceived():
                if isSignalToShutdownReceived():
                    shutdown_signal_received = True
                    break
                sleep(1)

            if not isSignalToStandByReceived():

                logger.info(f'{this_script}: resume signal received')

                logger.info(f'{this_script}: reload configuration')

                configuration.read()

                leds_rear.set_intensity(0)
                leds_front.set_intensity(0)
                leds_uv.set_intensity(0)
                leds_deported.set_intensity(0)

                if configuration.leds['mode'] == 1:
                    leds_rear.set_intensity(configuration.leds['intensity_rear'])
                    logger.info(f'{this_script}: LEDs rear set')
                if configuration.leds['mode'] == 1 or configuration.leds['mode'] == 2:
                    leds_front.set_intensity(configuration.leds['intensity_front'])
                    logger.info(f'{this_script}: LEDs front set')
                if configuration.leds['mode'] == 2:
                    leds_uv.set_intensity(configuration.leds['intensity_uv'])
                    leds_uv.turn_on()
                    logger.info(f'{this_script}: LEDs uv set')
                if configuration.leds['mode'] == 3:
                    leds_deported.set_intensity(configuration.leds['intensity_deported'])
                    logger.info(f'{this_script}: LEDs deported set')

                if AI_AVAILABLE and configuration.ai_detection['enable']:

                    logger.info(f'{this_script}: AI detection enabled')

                    if ai_model is None:
                        ai_model = YOLO(AI_MODEL) # load .pt file

                        logger.info(f'{this_script}: YOLO ai_model loaded => {AI_MODEL}')
                        logger.info(f"{this_script}: detection using images of size {configuration.ai_detection['image_width']}x{configuration.ai_detection['image_height']}")
                        logger.info(f"{this_script}: detection using minimal confidence of {configuration.ai_detection['min_confidence']}")

                else:

                    ai_model = None
                    logger.info(f'{this_script}: AI detection disabled')


        if isSignalToShutdownReceived() or shutdown_signal_received:
            logger.info(f'{this_script}: shutdown signal received')
            break

        sleep(0.1)

    logger.info(f'{this_script}: stop capturing images')

    camera.stop()
    logger.info(f'{this_script}: camera stopped')

    if configuration.leds['mode'] == 1:
        leds_rear.turn_off()
    if configuration.leds['mode'] == 1 or configuration.leds['mode'] == 2:
        leds_front.turn_off()
    if configuration.leds['mode'] == 2:
        leds_uv.turn_off()
    if configuration.leds['mode'] == 3:
        leds_deported.turn_off()

    logger.info(f'{this_script}: stop')

if __name__=='__main__':

    main()

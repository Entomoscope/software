import os
from time import time, sleep
from datetime import datetime

import logging
from logging.handlers import RotatingFileHandler

import pigpio

pi = pigpio.pi()

from configuration2 import Configuration2

from peripherals.microphone2 import Microphone2
from peripherals.pinout2 import SOUNDS_CAPTURE_ACTIVITY_PIN, SHUTDOWN_PIN, STARTUP_PIN

from globals_parameters import SOUNDS_CAPTURE_FOLDER, LOGS_DESKTOP_FOLDER, TODAY, MICROPHONE_DETECTION_INTERVAL, MICROPHONE_DETECTION_NUM_TRIES

this_script = os.path.basename(__file__)[:-3]

def isStartupCompleted():

    return pi.read(STARTUP_PIN)

def isSignalToShutdownReceived():

    return pi.read(SHUTDOWN_PIN)

def isSignalToStandByReceived():

    return pi.read(SOUNDS_CAPTURE_ACTIVITY_PIN)

def main():

    today_log_path = os.path.join(LOGS_DESKTOP_FOLDER, TODAY)
    if not os.path.exists(today_log_path):
        os.mkdir(today_log_path)

    logger = logging.getLogger('entomoscope_sounds_capture2')
    filename = os.path.join(today_log_path, TODAY + '_' + this_script + '.log')
    file_handler = RotatingFileHandler(filename, mode="a", maxBytes=10000, backupCount=100, encoding="utf-8")
    logger.addHandler(file_handler)
    formatter = logging.Formatter('%(asctime)s;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
    file_handler.setFormatter(formatter)
    logger.setLevel("DEBUG")

    while not isStartupCompleted():
        if isSignalToShutdownReceived():
            exit()
        sleep(0.5)

    logger.info('****************************')

    logger.info('sounds capture script started')

    logger.info(f'sounds capture folder: {SOUNDS_CAPTURE_FOLDER}')

    if isSignalToStandByReceived():

        logger.info('in standby mode. Wait for resume signal to start capturing sounds')

        while isSignalToStandByReceived():
            if isSignalToShutdownReceived():
                logger.info('shutdown signal received')
                logger.info('sounds capture stopped')
                exit()

            sleep(0.5)

        logger.info('resume signal received')

    configuration = Configuration2()
    logger.info('configuration file read')

    for i in range(0, MICROPHONE_DETECTION_NUM_TRIES):

        logger.info(f'Detecting the microphone ({i}/{MICROPHONE_DETECTION_NUM_TRIES} tries)')

        microphone = Microphone2(configuration.microphone['sample_rate'], configuration.microphone['gain'])

        if microphone.available:
            break
        else:
            start_detect_time = time()
            while (time() - start_detect_time) < MICROPHONE_DETECTION_INTERVAL:

                if isSignalToShutdownReceived():
                    logger.info('shutdown signal received')
                    logger.info('sounds capture stopped')
                    exit()

                sleep(0.5)

    if microphone.available:

        logger.info('microphone found')

        global_time = time()

        microphone.start()

        if microphone.stream:

            logger.info(f'microphone started at sample rate {microphone.sample_rate} Hz')
            logger.info(f"sound capture duration {configuration.sounds_capture['duration']} seconds")

            shutdown_signal_received = False
            standby_signal_received = False

            on_duration = configuration.schedule['on_duration']
            off_duration = configuration.schedule['off_duration']

            logger.info(f"on duration: {configuration.schedule['on_duration']} seconds")
            logger.info(f"off duration: {configuration.schedule['off_duration']} seconds")

            now_str = datetime.now().strftime('%Y%m%d%H%M%S')
            file_path = os.path.join(SOUNDS_CAPTURE_FOLDER, 'configuration_' + now_str + '.json')
            configuration.copy_to(file_path)
            logger.info(f'configuration file saved to {file_path}')

            on = True
            off = not(on)
            force_on = True

            try:
                now = datetime.now()
                configuration_startup_hour = int(configuration.schedule['next_startup'][11:13])
                configuration_startup_minute = int(configuration.schedule['next_startup'][14:16])
                t = datetime(now.year, now.month, now.day, configuration_startup_hour, configuration_startup_minute, 0)
                delta = t-now
                logger.info(f'wait {delta.seconds} seconds for full minute before capturing sounds')
                while (now < t):
                    sleep(0.1)
                    now = datetime.now()
            except BaseException as e:
                logger.error(str(e))

            previous_on_time = time()
            previous_off_time = time()

            logger.info('start capturing sounds')

            while True:

                try:

                    if on and (time() - previous_on_time > on_duration):

                        previous_off_time = time()
                        on = False
                        off = True
                        logger.info('sounds capture off')

                    if (off and (time() - previous_off_time > off_duration)) or force_on:

                        previous_on_time = time()
                        previous_capture_time = 0
                        force_on = False
                        on = True
                        off = False
                        logger.info('sounds capture on')

                    if on:

                        now_str = datetime.now().strftime('%Y%m%d%H%M%S')

                        file_path = os.path.join(SOUNDS_CAPTURE_FOLDER, now_str + '.wav')

                        data = []
                        total_samples = microphone.sample_rate * configuration.sounds_capture['duration']

                        logger.info('start recording')

                        while total_samples > 0:

                            samples = min(total_samples, microphone.CHUNK_SIZE)
                            data.append(microphone.stream.read(samples, exception_on_overflow=False))
                            total_samples -= samples

                            if isSignalToStandByReceived():
                                standby_signal_received = True
                                logger.info('standby signal received. Sounds capture paused')
                                break

                            if isSignalToShutdownReceived():
                                shutdown_signal_received = True
                                logger.info('shutdown signal received. Sounds capture stopped')
                                break

                        logger.info('stop recording')

                        microphone.save_recording(file_path, data)
                        logger.info(f'recording saved to {file_path}')

                    if isSignalToStandByReceived() or standby_signal_received:

                        logger.info('in standby mode. Wait for signal to resume')

                        while isSignalToStandByReceived():
                            if isSignalToShutdownReceived():
                                shutdown_signal_received = True
                                break
                            sleep(0.5)

                        if not isSignalToStandByReceived():

                            logger.info('resume signal received')
                            standby_signal_received = False

                            configuration.read()
                            logger.info('configuration read')

                            now_str = datetime.now().strftime('%Y%m%d%H%M%S')
                            file_path = os.path.join(SOUNDS_CAPTURE_FOLDER, 'configuration_' + now_str + '.json')
                            configuration.copy_to(file_path)
                            logger.info(f'configuration file saved to {file_path}')

                            logger.info(f"sound capture duration {configuration.sounds_capture['duration']} seconds")

                            on_duration = configuration.schedule['on_duration']
                            off_duration = configuration.schedule['off_duration']

                            logger.info(f"on duration: {configuration.schedule['on_duration']} seconds")
                            logger.info(f"off duration: {configuration.schedule['off_duration']} seconds")

                    if isSignalToShutdownReceived() or shutdown_signal_received:
                        logger.info('shutdown signal received')
                        break

                except BaseException as e:

                    logger.error(str(e))

                    break

        else:

            logger.error('audio stream not opened')

        microphone.stop()

    else:

        logger.error('microphone not found')

        pi.write(SOUNDS_CAPTURE_ACTIVITY_PIN, 1)

    logger.info(f'sounds capture stopped')

if __name__=='__main__':

    main()

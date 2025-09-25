import os
from time import time, sleep
from datetime import datetime

import logging
from logging.handlers import RotatingFileHandler

import pigpio

pi = pigpio.pi()

from configuration2 import Configuration2

from peripherals.microphone2 import Microphone2
from peripherals.pinout import SOUNDS_CAPTURE_ACTIVITY_PIN, SHUTDOWN_PIN

from globals_parameters import SOUNDS_CAPTURE_FOLDER, LOGS_DESKTOP_FOLDER, TODAY

this_script = os.path.basename(__file__)[:-3]

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

    logger.info('started.')

    logger.info(f'sounds capture folder: {SOUNDS_CAPTURE_FOLDER}')

    if isSignalToStandByReceived():

        logger.info('in standby mode. Wait for resume signal to start capturing sounds')

        while isSignalToStandByReceived():

            if isSignalToShutdownReceived():

                logger.info('shutdown signal received')
                logger.info('stopped')
                exit()

            sleep(0.5)

        logger.info('resume signal received')

    configuration = Configuration2()
    logger.info('configuration file read')

    num_max_tries = 15

    for i in range(0, num_max_tries):

        logger.info(f'try to find the microphone and open stream {i}/{num_max_tries}')

        microphone = Microphone2()

        if microphone.stream:
            break
        else:
            sleep(5)

    if microphone.available:

        logger.info('microphone found')

        global_time = time()

        microphone.start()

        if microphone.stream:

            logger.info(f'microphone started at sample rate {microphone.sample_rate} Hz')
            logger.info(f"sound capture duration {configuration.sounds_capture['duration']} seconds")

            shutdown_signal_received = False
            standby_signal_received = False

            on_duration = configuration.schedule['on_duration'] * 60
            off_duration = configuration.schedule['off_duration'] * 60

            logger.info(f"on duration: {configuration.schedule['on_duration']} minutes")
            logger.info(f"off duration: {configuration.schedule['off_duration']} minutes")

            on = True
            off = not(on)

            if on:
                logger.info('sounds capture on')

            previous_on_time = time()
            previous_off_time = time()

            now_str = datetime.now().strftime('%Y%m%d%H%M%S')
            file_path = os.path.join(SOUNDS_CAPTURE_FOLDER, 'configuration_' + now_str + '.json')
            configuration.copy_to(file_path)
            logger.info(f'configuration file saved to {file_path}')

            logger.info('start capturing sounds')

            while True:

                try:

                    if on and (time() - previous_on_time > on_duration):

                        previous_off_time = time()
                        on = False
                        off = True
                        logger.info('sounds capture off')

                    if off and (time() - previous_off_time > off_duration):

                        previous_on_time = time()
                        previous_capture_time = 0
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

                            on_duration = configuration.schedule['on_duration'] * 60
                            off_duration = configuration.schedule['off_duration'] * 60

                            logger.info(f"on duration: {configuration.schedule['on_duration']} minutes")
                            logger.info(f"off duration: {configuration.schedule['off_duration']} minutes")

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

    logger.info('stopped')

if __name__=='__main__':

    main()

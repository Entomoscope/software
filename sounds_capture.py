import os
from time import time, sleep
from datetime import datetime
import logging

import pigpio

pi = pigpio.pi()

from configuration import Configuration

from peripherals.microphone import Microphone
from peripherals.pinout import SOUNDS_CAPTURE_ACTIVITY_PIN, SHUTDOWN_PIN

from globals_parameters import SOUNDS_CAPTURE_FOLDER, LOGS_FOLDER, TODAY

this_script = os.path.basename(__file__)[:-3]

def isSignalToShutdownReceived():

    return pi.read(SHUTDOWN_PIN)

def isSignalToStandByReceived():

    return pi.read(SOUNDS_CAPTURE_ACTIVITY_PIN)

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

    microphone = Microphone()

    if microphone.available:

        logger.info(f'{this_script}: microphone found')

        global_time = time()

        microphone.start()

        shutdown_signal_received = False
        standby_signal_received = False

        logger.info(f'{this_script}: sample rate {microphone.sample_rate} Hz')

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

        while True:

            try:

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

                if on:

                    now_str = datetime.now().strftime('%Y%m%d%H%M%S')

                    # print(now_str)

                    file_path = os.path.join(SOUNDS_CAPTURE_FOLDER, now_str + '.wav')

                    data = []
                    total_samples = microphone.sample_rate * configuration.sounds_capture['duration']

                    while total_samples > 0:

                        samples = min(total_samples, microphone.chunk_size)
                        data.append(microphone.stream.read(samples, exception_on_overflow=False))
                        total_samples -= samples

                        if isSignalToStandByReceived():
                            standby_signal_received = True
                            logger.info(f'{this_script}: standby signal received. Sounds recording stopped')
                            break

                        if isSignalToShutdownReceived():
                            shutdown_signal_received = True
                            logger.info(f'{this_script}: shutdown signal received. Sounds recording stopped')
                            break

                    microphone.save_recording(file_path, data)

                if isSignalToStandByReceived() or standby_signal_received:
                    logger.info(f'{this_script}: in standby mode. Wait for signal to resume')
                    while isSignalToStandByReceived():
                        if isSignalToShutdownReceived():
                            shutdown_signal_received = True
                            break
                        sleep(1)
                    if not isSignalToStandByReceived():
                        logger.info(f'{this_script}: resume signal received')
                        configuration.read()

                if isSignalToShutdownReceived() or shutdown_signal_received:
                    logger.info(f'{this_script}: shutdown signal received')
                    break

            except BaseException as e:

                print(str(e))

                break

        microphone.stop()

    else:

        logger.error(f'{this_script}: microphone not found')

    logger.info(f'{this_script}: stop')

if __name__=='__main__':

    main()

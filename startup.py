#! /usr/bin/python3
import os
from datetime import datetime
import logging

import pigpio

from peripherals.pinout import IMAGES_CAPTURE_ACTIVITY_PIN, SOUNDS_CAPTURE_ACTIVITY_PIN, SHUTDOWN_PIN
from peripherals.externaldrive import ExternalDrive

from globals_parameters import STARTUP_FOLDER

from configuration import Configuration

def main():

    this_script = os.path.basename(__file__)[:-3]

    today = datetime.now().strftime('%Y%m%d')

    today_path = os.path.join(STARTUP_FOLDER, today)
    if not os.path.exists(today_path):
        os.mkdir(today_path)

    log_path = os.path.join(today_path, 'Logs')

    if not os.path.exists(log_path):
        os.mkdir(log_path)

    logger = logging.getLogger('main')
    filename = os.path.join(log_path, today + '_' + this_script + '.log')
    logging.basicConfig(filename=filename,
                        format='%(asctime)s;%(levelname)s;"%(message)s"',
                        encoding='utf-8',
                        datefmt='%d/%m/%Y;%H:%M:%S',
                        level=logging.DEBUG)

    logger.info('Starting the system...')

    configuration = Configuration()

    logger.info('Configuration loaded')

    external_drive = ExternalDrive()

    if external_drive.last_error:

        logger.error('External drive ' + external_drive.last_error)

    else:

        if external_drive.mounted:
            logger.info('External drive mounted')
        else:
            logger.warning('External drive not mounted')

        logger.info('  Path: ' + external_drive.path)
        logger.info('  UUID: ' + external_drive.uuid)
        logger.info('  Mounted: ' + ('True' if external_drive.mounted else 'False'))
        logger.info(f'  Size: {external_drive.size}')
        logger.info(f'  Used: {external_drive.used}%')
        logger.info('  Target: ' + external_drive.target)

    pi = pigpio.pi()

    pi.write(SHUTDOWN_PIN, 0)

    if configuration.images_capture['enable']:
        pi.write(IMAGES_CAPTURE_ACTIVITY_PIN, 0)
        logger.info(f'GPIO{IMAGES_CAPTURE_ACTIVITY_PIN:02d} set to LOW to enable images capture')
    else:
        pi.write(IMAGES_CAPTURE_ACTIVITY_PIN, 1)
        logger.info(f'GPIO{IMAGES_CAPTURE_ACTIVITY_PIN:02d} set to HIGH to disable images capture')

    if configuration.sounds_capture['enable']:
        pi.write(SOUNDS_CAPTURE_ACTIVITY_PIN, 0)
        logger.info(f'GPIO{SOUNDS_CAPTURE_ACTIVITY_PIN:02d} set to LOW to enable sounds capture')
    else:
        pi.write(SOUNDS_CAPTURE_ACTIVITY_PIN, 1)
        logger.info(f'GPIO{SOUNDS_CAPTURE_ACTIVITY_PIN:02d} set to HIGH to disable sounds capture')

    logger.info('System started')

if __name__ == '__main__':

    main()

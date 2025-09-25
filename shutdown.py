import os
import pigpio
from time import sleep
import logging
from datetime import datetime

from peripherals.wittypi import WittyPi
from peripherals.externaldisk import ExternalDisk
from peripherals.pinout import SHUTDOWN_PIN
from globals_parameters import LOGS_DESKTOP_FOLDER, TODAY, TOMORROW, DELAY_BEFORE_SHUTDOWN, PYTHON_SCRIPTS_BASE_FOLDER, TMP_FOLDER

from logsfiles import LogsFiles

from configuration2 import Configuration2

if __name__ == '__main__':

    this_script = os.path.basename(__file__)[:-3]

    today_log_path = os.path.join(LOGS_DESKTOP_FOLDER, TODAY)
    if not os.path.exists(today_log_path):
        os.mkdir(today_log_path)

    logger = logging.getLogger('entomoscope_shutdown')
    filename = os.path.join(today_log_path, TODAY + '_' + this_script + '.log')
    file_handler = logging.FileHandler(filename, mode="a", encoding="utf-8")
    logger.addHandler(file_handler)
    formatter = logging.Formatter('%(asctime)s;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
    file_handler.setFormatter(formatter)
    logger.setLevel("DEBUG")

    logger.info('shutting down the entomoscope')

    pi = pigpio.pi()

    pi.write(SHUTDOWN_PIN, 1)

    logger.info(f'shutdown signal send on pin {SHUTDOWN_PIN}')

    sleep(DELAY_BEFORE_SHUTDOWN-2)

    # external_disk = ExternalDisk()

    # if not external_disk.available:
        # logger.info('external disk not found')
    # else:
        # logger.info('external disk found')
        # external_disk.unmount()

    if os.path.exists(TMP_FOLDER):
        os.rmdir(TMP_FOLDER)
        logger.info('remove temporary folder ' + TMP_FOLDER)

    tmp_wav_file = os.path.join(PYTHON_SCRIPTS_BASE_FOLDER, 'static', 'tmp.wav')

    if os.path.exists(tmp_wav_file):
        os.remove(tmp_wav_file)
        logger.info('remove temporary wav file ' + tmp_wav_file)

    witty_pi = WittyPi()

    if witty_pi.get_latest_action_reason_code() == witty_pi.ALARM_SHUTDOWN:
        logger.info('shutdown due to RTC alarm')
    elif witty_pi.get_latest_action_reason_code() == witty_pi.BUTTON_CLICKED:
        logger.info('shutdown due to button pressed by user')
    else:
        logger.info(f'shutdown due to {witty_pi.get_latest_action_reason()}')

    configuration = Configuration2()

    logger.info('configuration read')

    if configuration.schedule['enable']:

        if witty_pi.get_latest_action_reason_code() == witty_pi.ALARM_SHUTDOWN:

            if configuration.images_capture['mode'].lower() != 'lepinoc':

                alarm = witty_pi.get_shutdown_alarm()

                if alarm[3] == -1 or alarm[2] == -1 and alarm[1] == -1:

                    logger.info(f'shutdown alarm not shifted because wrong values ({alarm[3]} {alarm[2]}:{alarm[1]})')

                else:

                    alarm[3] = int(TOMORROW[6:])

                    witty_pi.set_shutdown_alarm(alarm[3], alarm[2], alarm[1])

                    configuration.schedule['next_shutdown'] = '-'.join([TOMORROW[:4], TOMORROW[4:6], TOMORROW[6:]]) + f' {alarm[2]:02d}:{alarm[1]:02d}'
                    configuration.save()

                    logger.info(f"shutdown alarm shifted to {configuration.schedule['next_shutdown']} {datetime.now().astimezone().strftime('%Z')}")

        elif witty_pi.get_latest_action_reason_code() == witty_pi.BUTTON_CLICKED:

            logger.info('shutdown alarm not shifted')

        else:

            logger.info('shutdown alarm not shifted')

    else:

        logger.info('scheduler is disabled')

    logs_files = LogsFiles()
    logs_files.backup()
    logger.info('logs files backuped')

    # logger.info('backup and clear today logs files')
    # logs_files.clear()

    logger.info('system shutdowned')

    sleep(0.5)

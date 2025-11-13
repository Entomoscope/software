#! /usr/bin/python3

import os
from datetime import datetime, timedelta, timezone
import logging

from subprocess import check_output

import pigpio

from peripherals.pinout2 import IMAGES_CAPTURE_ACTIVITY_PIN, SOUNDS_CAPTURE_ACTIVITY_PIN, SHUTDOWN_PIN, STARTUP_PIN
from peripherals.wittypi import WittyPi
from peripherals.externaldisk import ExternalDisk
from ephemeris import Ephemeris
from date_time import DateTime

from globals_parameters import LOGS_DESKTOP_FOLDER, TODAY, TODAY_NOW, TOMORROW, TOMORROW_NOW

from configuration2 import Configuration2

pi = pigpio.pi()

pi.write(SHUTDOWN_PIN, 0)
pi.write(STARTUP_PIN, 0)

def main():

    this_script = os.path.basename(__file__)[:-3]

    today_log_path = os.path.join(LOGS_DESKTOP_FOLDER, TODAY)
    if not os.path.exists(today_log_path):
        os.mkdir(today_log_path)

    logger = logging.getLogger('entomoscope_startup2')
    filename = os.path.join(today_log_path, TODAY + '_' + this_script + '.log')
    file_handler = logging.FileHandler(filename, mode="a", encoding="utf-8")
    logger.addHandler(file_handler)
    formatter = logging.Formatter('XX/XX/XXXX;XX:XX:XX;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"')
    file_handler.setFormatter(formatter)
    logger.setLevel("DEBUG")

    logger.info('****************************')

    logger.info('starting up the system')

    witty_pi = WittyPi()

    witty_pi.get_date()

    dateTime = DateTime()

    dateTime.set_time(witty_pi.year, witty_pi.month, witty_pi.day, witty_pi.hour, witty_pi.minute, witty_pi.second)

    formatter = logging.Formatter('%(asctime)s;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
    file_handler.setFormatter(formatter)

    logger.info(f'system time set to: "{witty_pi.day:02d}/{witty_pi.month:02d}/{2000+witty_pi.year} {witty_pi.hour:02d}:{witty_pi.minute:02d}:{witty_pi.second:02d}"')

    if witty_pi.get_latest_action_reason_code() == witty_pi.ALARM_STARTUP:
        logger.info('startup due to RTC alarm')
    elif witty_pi.get_latest_action_reason_code() == witty_pi.BUTTON_CLICKED:
        logger.info('startup due to button pressed by user')
    else:
        logger.info(f'startup due to {witty_pi.get_latest_action_reason()}')

    configuration = Configuration2()

    logger.info('configuration read')

    if configuration.schedule['enable']:

        if witty_pi.get_latest_action_reason_code() == witty_pi.ALARM_STARTUP:

            lepinoc_startup_set = False

            if configuration.mode['mode'].lower() == 'lepinoc':

                ephemeris = Ephemeris()

                if ephemeris.file_found:

                    if ephemeris.tomorrow_setting['str']:

                        next_shutdown = datetime(TODAY_NOW.year, TODAY_NOW.month, TODAY_NOW.day, ephemeris.today_setting['hour'], ephemeris.today_setting['minute'], 0, 0, tzinfo=timezone.utc) + timedelta(hours=4) + timedelta(minutes=5)
                        next_shutdown = next_shutdown.astimezone()

                        configuration.schedule['next_shutdown'] = next_shutdown.strftime('%Y-%m-%d %H:%M')

                        logger.info('Lepinoc shutdown alarm set to ' + next_shutdown.strftime('%Y-%m-%d %H:%M %Z'))

                        next_startup = datetime(TOMORROW_NOW.year, TOMORROW_NOW.month, TOMORROW_NOW.day, ephemeris.tomorrow_setting['hour'], ephemeris.tomorrow_setting['minute'], 0, 0, tzinfo=timezone.utc)
                        next_startup = next_startup.astimezone()

                        configuration.schedule['next_startup'] = next_startup.strftime('%Y-%m-%d %H:%M')

                        logger.info('Lepinoc startup alarm shifted to ' + next_startup.strftime('%Y-%m-%d %H:%M %Z'))

                        configuration.save()

                        next_startup = next_startup - timedelta(minutes=1)

                        witty_pi.set_startup_alarm(next_startup.day, next_startup.hour, next_startup.minute)

                        lepinoc_startup_set = True

                    else:

                        logger.error(f'Lepinoc startup alarm not shifted because tomorrow ({TOMORROW}) setting not found in ' + ephemeris.file)
                        logger.warning('try classical one day shift')
                        lepinoc_startup_set = False

                else:

                    logger.error(f'Lepinoc startup alarm not shifted because file not found: ' + ephemeris.file)
                    logger.warning(f'try classical one day shift')
                    lepinoc_startup_set = False

            if not lepinoc_startup_set:

                startup_date = [int(x) for x in configuration.schedule['next_startup'].replace('-', ' ').replace(':', ' ').split()]
                startup_date = datetime(startup_date[0], startup_date[1], startup_date[2], startup_date[3], startup_date[4], 0, 0)

                # next_startup = datetime(TOMORROW_NOW.year, TOMORROW_NOW.month, TOMORROW_NOW.day, ephemeris.tomorrow_setting['hour'], ephemeris.tomorrow_setting['minute'], 0, 0, tzinfo=timezone.utc)
                # next_startup = next_startup.astimezone()

                next_startup = startup_date + timedelta(hours=24)

                configuration.schedule['next_startup'] = next_startup.strftime('%Y-%m-%d %H:%M')

                # configuration.schedule['next_startup'] = '-'.join([TOMORROW[:4], TOMORROW[4:6], TOMORROW[6:]]) + f' {alarm[2]:02d}:{alarm[1]:02d}'
                configuration.save()

                logger.info(f"startup alarm shifted to {configuration.schedule['next_startup']} {datetime.now().astimezone().strftime('%Z')}")

                next_startup = next_startup - timedelta(minutes=1)

                witty_pi.set_startup_alarm(next_startup.day, next_startup.hour, next_startup.minute)

                # alarm = witty_pi.get_startup_alarm()

                # if alarm[3] == -1 or alarm[2] == -1 and alarm[1] == -1:

                    # logger.info(f'startup alarm not shifted because wrong values ({alarm[3]} {alarm[2]}:{alarm[1]})')

                # else:

                    # alarm[3] = int(TOMORROW[6:])

                    # witty_pi.set_startup_alarm(alarm[3], alarm[2], alarm[1])

                    # configuration.schedule['next_startup'] = '-'.join([TOMORROW[:4], TOMORROW[4:6], TOMORROW[6:]]) + f' {alarm[2]:02d}:{alarm[1]:02d}'
                    # configuration.save()

                    # logger.info(f"startup alarm shifted to {configuration.schedule['next_startup']} {datetime.now().astimezone().strftime('%Z')}")

        elif witty_pi.get_latest_action_reason_code() == witty_pi.BUTTON_CLICKED:

            logger.info('startup alarm not shifted')

        else:

            logger.info('startup alarm not shifted')

    else:

        logger.info('scheduler is disabled')

    external_disk = ExternalDisk()

    if not external_disk.available:
        logger.warning('external disk not found')
    else:
        external_disk.mount()
        if external_disk.mounted:
            logger.info('external disk found and mounted')
            external_disk.get_info()
        else:
            logger.warning('external disk found but not mounted')

    if configuration.images_capture['enable'] and (witty_pi.get_latest_action_reason_code() == witty_pi.ALARM_STARTUP or witty_pi.get_latest_action_reason_code() == witty_pi.ALARM1_DELAYED):
        pi.write(IMAGES_CAPTURE_ACTIVITY_PIN, 0)
        logger.info(f'GPIO{IMAGES_CAPTURE_ACTIVITY_PIN:02d} set to 0')
        logger.info(f'images capture started')
    else:
        pi.write(IMAGES_CAPTURE_ACTIVITY_PIN, 1)
        logger.info(f'GPIO{IMAGES_CAPTURE_ACTIVITY_PIN:02d} set to 1')
        logger.info(f'images capture paused')

    if configuration.sounds_capture['enable'] and (witty_pi.get_latest_action_reason_code() == witty_pi.ALARM_STARTUP or witty_pi.get_latest_action_reason_code() == witty_pi.ALARM1_DELAYED):
        pi.write(SOUNDS_CAPTURE_ACTIVITY_PIN, 0)
        logger.info(f'GPIO{SOUNDS_CAPTURE_ACTIVITY_PIN:02d} set to 0')
        logger.info(f'sounds capture started')
    else:
        pi.write(SOUNDS_CAPTURE_ACTIVITY_PIN, 1)
        logger.info(f'GPIO{SOUNDS_CAPTURE_ACTIVITY_PIN:02d} set to 1')
        logger.info(f'sounds capture paused')

    pi.write(STARTUP_PIN, 1)

    logger.info('startup completed')

if __name__ == '__main__':

    main()

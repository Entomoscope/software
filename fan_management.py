#! /usr/bin/python3

import os

import logging
from logging.handlers import RotatingFileHandler

from datetime import datetime

from gpiozero import CPUTemperature

from configuration2 import Configuration2

from globals_parameters import LOGS_DESKTOP_FOLDER, TODAY

from peripherals.fan import Fan
from peripherals.pinout import FAN_PIN

# This scripts should be run in background using crontab
# Use "crontab -e" to edit the crontab file
# Use "crontab -l" to see the crontab file content

# To run the script every 2 minutes, add this line in the crontab file:
# */2 * * * * /usr/bin/python /home/entomoscope/Entomoscope/fan_management.py 2>&1 | logger -t fan_mng_entomoscope

# To search for all errors
# journalctl -t fan_mng_entomoscope
# To search for errors since last boot
# journalctl -b -t fan_mng_entomoscope
# To search for errors since yesterday
# journalctl -t fan_mng_entomoscope --since yesterday
# To search for errors since today
# journalctl -t fan_mng_entomoscope --since today
# To search for errors since a date
# journalctl -t fan_mng_entomoscope --since "YYYY-MM-DD HH:MM:SS"


def main():

    this_script = os.path.basename(__file__)[:-3]

    today_log_path = os.path.join(LOGS_DESKTOP_FOLDER, TODAY)
    if not os.path.exists(today_log_path):
        os.mkdir(today_log_path)

    logger = logging.getLogger('entomoscope_fan_management')
    filename = os.path.join(today_log_path, TODAY + '_' + this_script + '.log')
    file_handler = RotatingFileHandler(filename, mode="a", maxBytes=50000, backupCount=100, encoding="utf-8")
    logger.addHandler(file_handler)
    formatter = logging.Formatter('%(asctime)s;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
    file_handler.setFormatter(formatter)
    logger.setLevel("DEBUG")

    try:

        configuration = Configuration2()
        configuration.read()

        if configuration.cooling_system['enable']:

            cpu_temperature_levels = configuration.cooling_system['cpu_temperature_levels']

            if len(cpu_temperature_levels) != 4:
                logging.error(f'4 temperature levels required. {len(cpu_temperature_levels)} found')
                return

            if any([x<0 for x in cpu_temperature_levels]):
                logging.error('temperature levels must be greater than 0')
                return

            if any([x>80 for x in cpu_temperature_levels]):
                logging.error('temperature levels must be lower than 80')
                return

            fan_speed_levels = configuration.cooling_system['fan_speed_levels']

            if len(fan_speed_levels) != 4:
                logging.error(f'4 fan speed levels required. {len(fan_speed_levels)} found')
                return

            if any([x<0 for x in fan_speed_levels]):
                logging.error('fan speed levels must be greater than 0')
                return

            if any([x>100 for x in fan_speed_levels]):
                logging.error('fan speed levels must be lower than 100')
                return

            fan = Fan(FAN_PIN)

            cpu_temperature = CPUTemperature().temperature

            if cpu_temperature > cpu_temperature_levels[3]:

                fan.set_speed(fan_speed_levels[3])

                logger.info(f'CPU temperature: {cpu_temperature:.1f}°C => fan speed {fan_speed_levels[3]}%')

            elif cpu_temperature > cpu_temperature_levels[2]:

                fan.set_speed(fan_speed_levels[2])

                logger.info(f'CPU temperature: {cpu_temperature:.1f}°C => fan speed {fan_speed_levels[2]}%')

            elif cpu_temperature > cpu_temperature_levels[1]:

                fan.set_speed(fan_speed_levels[1])

                logger.info(f'CPU temperature: {cpu_temperature:.1f}°C => fan speed {fan_speed_levels[1]}%')

            elif cpu_temperature > cpu_temperature_levels[0]:

                fan.set_speed(fan_speed_levels[0])

                logger.info(f'CPU temperature: {cpu_temperature:.1f}°C => fan speed {fan_speed_levels[0]}%')

            else:

                fan.set_speed(0)

                logger.info(f'CPU temperature: {cpu_temperature:.1f}°C => fan speed 0%')

    except BaseException as e:

        logging.error(str(e))

if __name__ == '__main__':

    main()

#! /usr/bin/python3

import os
import logging
from datetime import datetime

from gpiozero import CPUTemperature

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

CPU_TEMP_LEVEL_1 = 65
CPU_TEMP_LEVEL_2 = 70
CPU_TEMP_LEVEL_3 = 75
CPU_TEMP_LEVEL_4 = 80

FAN_LEVEL_1 = 25
FAN_LEVEL_2 = 50
FAN_LEVEL_3 = 75
FAN_LEVEL_4 = 90

def main():

    this_script = os.path.basename(__file__)[:-3]

    today = datetime.now().strftime('%Y%m%d')

    user_path = os.path.expanduser('~')

    today_path = os.path.join(user_path, 'Desktop', today)

    if not os.path.exists(today_path):
        os.mkdir(today_path)

    log_path = os.path.join(user_path, 'Desktop', today, 'Logs')

    if not os.path.exists(log_path):
        os.mkdir(log_path)

    logger = logging.getLogger('main')
    filename = os.path.join(log_path, today + '_' + this_script + '.log')
    logging.basicConfig(filename=filename,
                        format='%(asctime)s;%(levelname)s;"%(message)s"',
                        encoding='utf-8',
                        datefmt='%d/%m/%Y;%H:%M:%S',
                        level=logging.DEBUG)
                        
    try:

        fan = Fan(FAN_PIN)

        cpu_temperature = CPUTemperature().temperature

        if cpu_temperature > CPU_TEMP_LEVEL_4:

                fan.set_speed(FAN_LEVEL_4)

                logger.info(f'{this_script}: CPU temperature: {cpu_temperature:.1f}°C => fan speed {FAN_LEVEL_4}%')
                
        elif cpu_temperature > CPU_TEMP_LEVEL_3:

                fan.set_speed(FAN_LEVEL_3)

                logger.info(f'{this_script}: CPU temperature: {cpu_temperature:.1f}°C => fan speed {FAN_LEVEL_3}%')

        elif cpu_temperature > CPU_TEMP_LEVEL_2:

                fan.set_speed(FAN_LEVEL_2)

                logger.info(f'{this_script}: CPU temperature: {cpu_temperature:.1f}°C => fan speed {FAN_LEVEL_2}%')

        elif cpu_temperature > CPU_TEMP_LEVEL_1:

                fan.set_speed(FAN_LEVEL_1)

                logger.info(f'{this_script}: CPU temperature: {cpu_temperature:.1f}°C => fan speed {FAN_LEVEL_1}%')

        else:

                fan.set_speed(0)

                logger.info(f'{this_script}: CPU temperature: {cpu_temperature:.1f}°C => fan speed 0%')


    except BaseException as e:

        logging.error(str(e))     
                        
if __name__ == '__main__':

    main()

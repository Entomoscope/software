#! /usr/bin/python3
import os
import logging
import csv
from datetime import datetime
from gpiozero import CPUTemperature
from globals_parameters import LOGS_DESKTOP_FOLDER, ENVIRONMENT_MONITORING_FOLDER, TODAY
from sensors.sht31 import SHT31
from peripherals.wittypi import WittyPi

# This scripts should be run in background using crontab
# Use "crontab -e" to edit the crontab file
# Use "crontab -l" to see the crontab file content

# To run the script every 5 minutes, add this line in the crontab file:
# */5 * * * * /usr/bin/python /home/entomoscope/Entomoscope/environment_monitoring.py 2>&1 | logger -t env_mon_entomoscope

# To search for all errors
# journalctl -t env_mon_entomoscope
# To search for errors since last boot
# journalctl -b -t env_mon_entomoscope
# To search for errors since yesterday
# journalctl -t env_mon_entomoscope --since yesterday
# To search for errors since today
# journalctl -t env_mon_entomoscope --since today
# To search for errors since a date
# journalctl -t env_mon_entomoscope --since "YYYY-MM-DD HH:MM:SS"

def main():

    this_script = os.path.basename(__file__)[:-3]

    today_log_path = os.path.join(LOGS_DESKTOP_FOLDER, TODAY)

    if not os.path.exists(today_log_path):
        os.mkdir(today_log_path)

    logger = logging.getLogger('entomoscope_environement_monitoring')
    filename = os.path.join(today_log_path, TODAY + '_' + this_script + '.log')
    file_handler = logging.FileHandler(filename, mode="a", encoding="utf-8")
    logger.addHandler(file_handler)
    formatter = logging.Formatter('%(asctime)s;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
    file_handler.setFormatter(formatter)
    logger.setLevel("DEBUG")

    try:

        sht31 = SHT31()

        sht31.get_temperature_humidity()

        wittypi = WittyPi()

        wittypi.get_info()

        cpu_temperature = CPUTemperature().temperature

        now = datetime.now().strftime('%H:%M')

        header = ['Time(UTC)', 'ExternalTemperature(C)', 'ExternalHumidity(%)', 'CpuTemperature(C)', 'Vin(V)', 'Vout(V)', 'Iout(A)']

        data = [now, f'{sht31.temperature:.1f}', f'{sht31.humidity:.1f}', f'{cpu_temperature:.1f}', f'{wittypi.input_voltage:.3f}', f'{wittypi.output_voltage:.3f}', f'{wittypi.output_current:.3f}']

        csv_file_path = os.path.join(ENVIRONMENT_MONITORING_FOLDER, TODAY + '_environment.csv')

        if not os.path.exists(csv_file_path):

            with open(csv_file_path, 'w', encoding='UTF-8', newline='') as csv_file:

                writer = csv.writer(csv_file, delimiter=';')

                writer.writerow(header)
                writer.writerow(data)

        else:

            with open(csv_file_path, 'a', encoding='UTF-8', newline='') as csv_file:

                writer = csv.writer(csv_file, delimiter=';')

                writer.writerow(data)

    except BaseException as e:

        logging.error(str(e))

if __name__ == '__main__':

    main()

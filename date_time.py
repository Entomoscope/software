#! /usr/bin/python3

import os
from subprocess import check_output, call, CalledProcessError

import logging
from logging.handlers import RotatingFileHandler

# sudo timedatectl set-ntp on
# sudo timedatectl set-ntp off

# date --set HH:MM:SS --utc

from globals_parameters import LOGS_DESKTOP_FOLDER, TODAY

this_script = os.path.basename(__file__)[:-3]

today_log_path = os.path.join(LOGS_DESKTOP_FOLDER, TODAY)
if not os.path.exists(today_log_path):
    os.mkdir(today_log_path)

logger = logging.getLogger('entomoscope_date_time')
filename = os.path.join(today_log_path, TODAY + '_' + this_script + '.log')
file_handler = RotatingFileHandler(filename, mode="a", maxBytes=50000, backupCount=100, encoding="utf-8")
logger.addHandler(file_handler)
formatter = logging.Formatter('%(asctime)s.%(msecs)03d;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
file_handler.setFormatter(formatter)
logger.setLevel("DEBUG")

class DateTime():

    def __init__(self):

        self.get_date()
        self.get_time()
        self.get_date_time_info()

    def get_date_time_info(self):

        try:

            info = [x.strip() for x in check_output('timedatectl', shell=True).decode('utf-8').split('\n')]

            self.date_time_info = [info[0], info[3]]

        except CalledProcessError as e:

            logger.error(str(e))

    def get_date(self):

        try:

            self.date = check_output('date "+%Y-%m-%d"', shell=True).decode('utf-8').strip()

        except CalledProcessError as e:

            logger.error(str(e))

    def get_time(self):

        try:

            self.time = check_output('date "+%H:%M:%S"', shell=True).decode('utf-8').strip()

        except CalledProcessError as e:

            logger.error(str(e))

    def set_time_utc(self, year, month, day, hours, minutes, seconds):

        try:

            cmd = f'sudo date --set "{year}-{month:02d}-{day:02d} {hours:02d}:{minutes:02d}:{seconds:02d}" --utc'

            call(cmd, shell=True)

        except CalledProcessError as e:

            logger.error(str(e))

    def set_date_time(self, year, month, day, hours, minutes, seconds):

        try:

            cmd = f'sudo date --set "{year}-{month:02d}-{day:02d} {hours:02d}:{minutes:02d}:{seconds:02d}"'

            call(cmd, shell=True)

        except CalledProcessError as e:

            logger.error(str(e))

    def set_date_time_2(self, date, time):

        try:

            cmd = f'sudo date --set "{date} {time}"'

            call(cmd, shell=True)

        except CalledProcessError as e:

            logger.error(str(e))

    def start_web_synchronisation(self):

        try:

            cmd = 'sudo timedatectl set-ntp on'

            call(cmd, shell=True)

        except CalledProcessError as e:

            logger.error(str(e))

    def stop_web_synchronisation(self):

        try:

            cmd = 'sudo timedatectl set-ntp off'

            call(cmd, shell=True)

        except CalledProcessError as e:

            logger.error(str(e))

    def __str__(self):

        s = ''

        s += 'Date: ' + self.date + '\n'
        s += 'Time: ' + self.time + '\n'
        s += '\n'.join(self.date_time_info)

        return s

if __name__ == '__main__':

    datetime = DateTime()

    print(datetime)

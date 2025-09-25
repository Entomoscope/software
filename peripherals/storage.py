#! /usr/bin/python3

import sys
import os
from subprocess import check_output

import logging

sys.path.append('..')

from peripherals.externaldisk import ExternalDisk
from globals_parameters import LOGS_DESKTOP_FOLDER, TODAY

this_script = os.path.basename(__file__)[:-3]

today_log_path = os.path.join(LOGS_DESKTOP_FOLDER, TODAY)
if not os.path.exists(today_log_path):
    os.mkdir(today_log_path)

logger = logging.getLogger('entomoscope_storage')
filename = os.path.join(today_log_path, TODAY + '_' + this_script + '.log')
file_handler = logging.FileHandler(filename, mode="a", encoding="utf-8")
logger.addHandler(file_handler)
formatter = logging.Formatter('%(asctime)s;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
file_handler.setFormatter(formatter)
logger.setLevel("DEBUG")

class Storage():

    def __init__(self, location):

        self.total = 0
        self.used = 0
        self.available = 0
        self.used_percent = 0

        if location == 'sd':
            self.name = 'SD card'
            self.path = '/'
            self.available = True
        elif location == 'external_disk':
            self.name = 'External disk'
            external_disk = ExternalDisk()
            self.path = external_disk.path
            self.available = external_disk.available
        else:
            self.path = None
            self.available = False

        self.get_data()

    def get_data(self):

        if self.available and self.path:

            try:

                output = check_output(['df', '-h', self.path]).decode('utf-8').split('\n')[1].split()

                self.total = output[1]
                self.used = output[2]
                self.available = output[3]
                self.used_percent = output[4]

            except BaseException as e:

                logger.error(str(e))

                self.total = ''
                self.used = ''
                self.available = ''
                self.used_percent = ''

    def __str__(self):

        return f'{self.name}\n  Path: {self.path}\n  Total: {self.total}\n  Used: {self.used} ({self.used_percent})\n  Available: {self.available}\n'

if __name__ == '__main__':

    sd_card = Storage('sd')

    print(sd_card)

    external_disk = Storage('external_disk')

    print(external_disk)

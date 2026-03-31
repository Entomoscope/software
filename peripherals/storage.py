#! /usr/bin/python3

import sys
import os
from subprocess import check_output, CalledProcessError

import logging

sys.path.append('..')

# from peripherals.externaldisk import ExternalDisk
from globals_parameters import LOGS_DESKTOP_FOLDER, TODAY, MEDIA_FOLDER

this_script = os.path.basename(__file__)[:-3]

today_log_path = os.path.join(LOGS_DESKTOP_FOLDER, TODAY)
if not os.path.exists(today_log_path):
    os.mkdir(today_log_path)

logger = logging.getLogger('entomoscope_storage')
filename = os.path.join(today_log_path, TODAY + '_' + this_script + '.log')
file_handler = logging.FileHandler(filename, mode="a", encoding="utf-8")
logger.addHandler(file_handler)
formatter = logging.Formatter('%(asctime)s.%(msecs)03d;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
file_handler.setFormatter(formatter)
logger.setLevel("DEBUG")

class Storage():

    def __init__(self, location):

        if location == 'sd':
            self.name = 'SD card'
            self.path = '/'
            self.available = True
        elif location == 'external_disk':
            self.name = 'External disk'
            self.find()
            # external_disk = ExternalDisk()
            # self.path = external_disk.path
            # self.available = external_disk.available
        else:
            self.path = None
            self.available = False

        self.get_data()

    def get_data(self):

        if self.available and self.path:

            try:

                output = check_output(['df', '-h', '-BG', self.path]).decode('utf-8').split('\n')[1].split()

                self.total = output[1]
                self.total_num = float(output[1].replace('G',''))
                self.used = output[2]
                self.used_num = float(output[2].replace('G',''))
                self.available = output[3]
                self.available_num = float(output[3].replace('G',''))
                self.used_percent = output[4]
                self.used_percent_num = float(output[4].replace('%',''))

            except BaseException as e:

                logger.error(str(e))

                self.total = ''
                self.total_num = None
                self.used = ''
                self.used_num = None
                self.available = ''
                self.available_num = None
                self.used_percent = ''
                self.used_percent_num = None

        else:

            self.total = None
            self.total_num = None
            self.used = None
            self.used_num = None
            self.available = None
            self.available_num = None
            self.used_percent = None
            self.used_percent_num = None

    def find(self):

        p = os.listdir(MEDIA_FOLDER)
        if p:
            self.path = os.path.join(MEDIA_FOLDER, p[0])
            self.available = True
        else:
            self.path = None
            self.available = False

    def eject(self):

        if self.available and self.path:

            try:
                logger.info(f'unmounting disk {self.path}')
                outputs = check_output(['sudo', 'eject', '--verbose', '--scsi', self.path]).decode('utf-8').split('\n')
                for output in outputs:
                    logger.info(output)
                self.path = None
                self.available = False
            except CalledProcessError as e:
                logger.error('unmounting disk failed')
                logger.error(str(e))

    def __str__(self):

        s = f'{self.name}\n'
        s += f'Path: {self.path}\n'
        s += f'Total: {self.total} ({self.total_num})\n'
        s += f'Used: {self.used} ({self.used_num})\n'
        s += f'Used %: {self.used_percent} ({self.used_percent_num})\n'
        s += f'Available: {self.available} ({self.available_num})\n'

        return s

if __name__ == '__main__':

    sd_card = Storage('sd')

    print(sd_card)

    external_disk = Storage('external_disk')

    print(external_disk)

    external_disk.eject()

#! /usr/bin/python3

import os
import logging

from globals_parameters import EPHEMERIS_FILE_PATH, LOGS_DESKTOP_FOLDER, TODAY, TODAY_NOW, TOMORROW, TOMORROW_NOW

this_script = os.path.basename(__file__)[:-3]

today_log_path = os.path.join(LOGS_DESKTOP_FOLDER, TODAY)
if not os.path.exists(today_log_path):
    os.mkdir(today_log_path)

logger = logging.getLogger('entomoscope_ephemeris')
logger.setLevel(logging.INFO)
h = logging.FileHandler(os.path.join(today_log_path, TODAY + '_' + this_script + '.log'))
f = logging.Formatter('%(asctime)s;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
h.setFormatter(f)
logger.addHandler(h)

class Ephemeris():

    # def __init__(self, location):
    def __init__(self):

        # self.file = os.path.join(EPHEMERIS_FILE_PATH, location + '.csv')
        self.file = os.path.join(EPHEMERIS_FILE_PATH, 'ephemeris.csv')

        self.file_found = os.path.exists(self.file)

        self.today_rising = {'str': None, 'hour': None, 'minute': None}
        self.today_setting = {'str': None, 'hour': None, 'minute': None}
        self.tomorrow_rising = {'str': None, 'hour': None, 'minute': None}
        self.tomorrow_setting = {'str': None, 'hour': None, 'minute': None}

        if self.file_found:
            self.read()
        else:
            logger.error('file not found: ' + self.file)

    def read(self):

        try:

            today = TODAY_NOW.strftime('%Y-%m-%d')
            tomorrow = TOMORROW_NOW.strftime('%Y-%m-%d')

            with open(self.file, 'r') as f:
                for line in f:
                    data = line.split(';')
                    if data[0].lower() == 'sun':
                        if data[1] == today:
                            self.today_rising['str'] = data[2]
                            self.today_rising['hour'], self.today_rising['minute'] = [int(x) for x in data[2].split(':')]
                            self.today_setting['str'] = data[6]
                            self.today_setting['hour'], self.today_setting['minute'] = [int(x) for x in data[6].split(':')]
                            logger.info(f"today rising: {self.today_rising['str']} UTC")
                            logger.info(f"today setting {self.today_setting['str']} UTC")
                        elif data[1] == tomorrow:
                            self.tomorrow_rising['str'] = data[2]
                            self.tomorrow_rising['hour'], self.tomorrow_rising['minute'] = [int(x) for x in data[2].split(':')]
                            self.tomorrow_setting['str'] = data[6]
                            self.tomorrow_setting['hour'], self.tomorrow_setting['minute'] = [int(x) for x in data[6].split(':')]
                            logger.info(f"tomorrow rising: {self.tomorrow_rising['str']} UTC")
                            logger.info(f"tomorrow setting: {self.tomorrow_setting['str']} UTC")
                            break

        except BaseException as e:

            logger.error('error reading file: ' + self.file)
            logger.error(str(e))

    def __str__(self):

        s = 'File: ' + self.file + '\n'
        s += f'Available: {self.file_found}\n'
        s += f"Today rising: {self.today_rising['str']} UTC\n"
        s += f"Today setting: {self.today_setting['str']} UTC\n"
        s += f"Tomorrow rising: {self.tomorrow_rising['str']} UTC\n"
        s += f"Tomorrow setting: {self.tomorrow_setting['str']} UTC\n"

        return s

if __name__ == '__main__':

    ephemeris = Ephemeris()

    if ephemeris.file_found:

        print(ephemeris)

    else:

        print('File not found: ' + ephemeris.file)

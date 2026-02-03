#! /usr/bin/python3

import os
import sys
from subprocess import check_output, CalledProcessError
from time import time, sleep

import logging
from logging.handlers import RotatingFileHandler

sys.path.append('..')

from globals_parameters import LOGS_DESKTOP_FOLDER, TODAY, INTERNET_CONNECTION_TRY_DURATION, WIFI_CONNECTION_TRY_DURATION, WIFI_AUTOCONNECT_AP

this_script = os.path.basename(__file__)[:-3]

today_log_path = os.path.join(LOGS_DESKTOP_FOLDER, TODAY)
if not os.path.exists(today_log_path):
    os.mkdir(today_log_path)

logger = logging.getLogger('entomoscope_wifi' + '_' + this_script)
filename = os.path.join(today_log_path, TODAY + '_' + this_script + '.log')
file_handler = RotatingFileHandler(filename, mode="a", maxBytes=50000, backupCount=100, encoding="utf-8")
logger.addHandler(file_handler)
formatter = logging.Formatter('%(asctime)s;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
file_handler.setFormatter(formatter)
logger.setLevel("DEBUG")

class Wifi():

    def __init__(self, uuid='xxxxxxxx'):

        self.ap_name = None
        self.ap_password = None
        self.saved_names = []
        self.available_names = []

        self.show()

        if self.ap_name:
            if self.ap_name.endswith('xxxxxxxx'):
                logger.info(f'Remove default AP connection {self.ap_name}')
                self.remove(self.ap_name)
                self.ap_name = None
            elif not self.ap_name.endswith(uuid):
                logger.info(f'Remove current AP connection with wrong UUID {self.ap_name}')
                self.remove(self.ap_name)
                self.ap_name = None

        if not self.ap_name:
            logger.info(f'Create AP connection using RPi UUID {uuid}')
            self.create_ap_connection(uuid, autoconnect=WIFI_AUTOCONNECT_AP)


    def show(self):

        try:

            output = check_output('sudo nmcli -c no -m multiline c show', shell=True).decode('utf-8').split('\n')

            names = [x.split(':')[1].strip() for x in output if x.startswith('NAME')]
            uuids = [x.split(':')[1].strip() for x in output if x.startswith('UUID')]
            types = [x.split(':')[1].strip() for x in output if x.startswith('TYPE')]
            # devices = [x.split(':')[1].strip() for x in output if x.startswith('DEVICE')]

            self.saved_names = []

            logger.info('Connections saved:')

            for name, typ, uuid in zip(names, types, uuids):
                if typ.lower() == 'wifi':
                    if name.startswith('Entomoscope-'):
                        self.ap_name = name
                        self.ap_uuid = uuid
                    else:
                        self.saved_names.append(name)

                    logger.info(f'  {name}')

        except CalledProcessError as e:

            error_string = self.get_nmcli_error(str(e))

            logger.error('Unable to show wifi connections')

            logger.error(error_string)

    def list(self):

        try:

            output = check_output('sudo nmcli -c no -m multiline d wifi list', shell=True).decode('utf-8').split('\n')

            names = [x.split(':')[1].strip() for x in output if x.startswith('SSID')]
            signals = [x.split(':')[1].strip() for x in output if x.startswith('SIGNAL')]

            self.available_names = []

            logger.info('Connections available:')

            for name, signal in zip(names, signals):
                # print(f'{name} {signal}')
                if name not in self.available_names:
                    self.available_names.append(name)
                    logger.info(f'  {name}')

        except CalledProcessError as e:

            error_string = self.get_nmcli_error(str(e))

            logger.error('Unable to list wifi connections')

            logger.error(error_string)

    def add(self, name, password):

        if name not in self.saved_names:

            try:

                logger.info(f'Add wifi connection {name}')

                output = check_output(f'sudo nmcli c add type wifi con-name "{name}" ssid "{name}" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "{password}" autoconnect no ifname wlan0', shell=True).decode('utf-8').split('\n')
                for out in output:
                    if out:
                        logger.info(out)

                self.show()

                success = True

            except CalledProcessError as e:

                error_string = self.get_nmcli_error(str(e))

                logger.error(f'Unable to add wifi connection {name}')

                logger.error(error_string)

                success = False

        else:

            logger.warning(f'Wifi connection {name} is already stored')
            success = False

        return success

    def remove(self, name):

        if name in self.saved_names or name == self.ap_name:

            try:

                logger.info(f'Remove wifi connection {name}')

                output = check_output(f'sudo nmcli c delete "{name}"', shell=True).decode('utf-8').split('\n')
                for out in output:
                    if out:
                        logger.info(out)

                self.show()

                success = True

            except CalledProcessError as e:

                error_string = self.get_nmcli_error(str(e))

                logger.error(f'Unable to remove wifi connection {name}')

                logger.error(error_string)

                success = False

        else:

            logger.warning(f'Wifi connection {name} not in stored list')
            success = False

        return success


    def create_ap_connection(self, uuid, autoconnect=False, password='entomoscope'):

        try:

            ssid = 'Entomoscope-' + uuid

            logger.info('Create AP wifi connection')

            output = check_output(f'sudo nmcli device wifi hotspot ssid "{ssid}" password "{password}" con-name "{ssid}"', shell=True).decode('utf-8').split('\n')
            for out in output:
                if out:
                    logger.info(out)

            output = check_output(f'sudo nmcli c down "{ssid}"', shell=True).decode('utf-8').split('\n')
            for out in output:
                if out:
                    logger.info(out)

            output = check_output(f'sudo nmcli c mod "{ssid}" 802-11-wireless.band bg autoconnect {"yes" if autoconnect else "no"}', shell=True).decode('utf-8').split('\n')
            for out in output:
                if out:
                    logger.info(out)

            if autoconnect:
                output = check_output(f'sudo nmcli -w {WIFI_CONNECTION_TRY_DURATION} c up "{ssid}"', shell=True).decode('utf-8').split('\n')
                for out in output:
                    if out:
                        logger.info(out)

            self.ap_name = ssid
            self.ap_password  = password

            logger.info('AP wifi connection created')
            logger.info(f'SSID: {ssid}')
            logger.info(f'Password: {password}')
            logger.info(f'Autoconnect: {autoconnect}')

            success = True

        except CalledProcessError as e:

            error_string = self.get_nmcli_error(str(e))

            logger.error('Unable to create AP wifi connection')

            logger.error(error_string)

            success = False

        return success


    def get_nmcli_error(self, exception_string):

        num = exception_string.split(' ')[-1].split('.')[0]

        if num == '0':
            error_string = 'Success – indicates the operation succeeded.'
        elif num == '1':
            error_string = 'Unknown or unspecified error.'
        elif num == '2':
            error_string = 'Invalid user input, wrong nmcli invocation.'
        elif num == '3':
            error_string = f'Timeout expired.'
        elif num == '4':
            error_string = 'Connection activation failed.'
        elif num == '5':
            error_string = 'Connection deactivation failed.'
        elif num == '6':
            error_string = 'Disconnecting device failed.'
        elif num == '7':
            error_string = 'Connection deletion failed.'
        elif num == '8':
            error_string = 'NetworkManager is not running.'
        elif num == '10':
            error_string = 'Connection, device, or access point does not exist.'
        elif num == '65':
            error_string = 'When used with --complete-args option, a file name is expected to follow.'
        else:
            error_string = f'Undefined error ({num})'

        return error_string

    def test_internet_connection(self):

        try:

            logger.info('Try to connect to internet')

            output = check_output(f'ping -c1 -I wlan0 -W{INTERNET_CONNECTION_TRY_DURATION} www.google.com', shell=True).decode('utf-8').split('\n')

            print(output)

            for out in output:
                if out:
                    logger.info(out)

            success = True

        except CalledProcessError as e:

            logger.error('Error trying to connect to internet')
            logger.error(str(e))

            success = False

        return success


    def __str__(self):

        s = 'Access point:\n'
        s += '  ' + self.ap_name + '\n'

        s += 'Station saved:\n'
        if len(self.saved_names) > 0:
            for name in self.saved_names:
                s += '  ' + name + '\n'
        else:
            s += '  <None>\n'

        s += 'Station available:\n'
        if len(self.available_names) > 0:
            for name in self.available_names:
                s += '  ' + name + '\n'
        else:
            s += '  <None>\n'

        return s

if __name__ == '__main__':

    wifi = Wifi(uuid='ede1b681')

    wifi.show()

    wifi.list()

    print(wifi)

    # success = wifi.test_internet_connection()

    # print(success)

import sys
import os
from subprocess import check_output
import platform

import logging

sys.path.append('..')

from globals_parameters import LOGS_DESKTOP_FOLDER, TODAY

this_script = os.path.basename(__file__)[:-3]

today_log_path = os.path.join(LOGS_DESKTOP_FOLDER, TODAY)
if not os.path.exists(today_log_path):
    os.mkdir(today_log_path)

logger = logging.getLogger('entomoscope_rpi')
filename = os.path.join(today_log_path, TODAY + '_' + this_script + '.log')
file_handler = logging.FileHandler(filename, mode="a", encoding="utf-8")
logger.addHandler(file_handler)
formatter = logging.Formatter('%(asctime)s;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
file_handler.setFormatter(formatter)
logger.setLevel("DEBUG")

class Rpi():

    def __init__(self):

        self.model = self.get_model()
        self.revision = self.get_revision()
        self.serial = self.get_serial()
        # self.ram = self.get_ram()

        self.hostname = self.get_hostname()

        self.cpu_temperature = self.get_temperature()

        self.wifi_ssid = self.get_wifi_ssid()

        self.ip_address = self.get_ip_address()

        self.pigpio_supported = not(self.model.startswith('Raspberry Pi 5'))

        self.os_version = self.get_os_version()

        self.arch_version = self.get_arch_version()

        self.wifi_power_save = self.get_wifi_power_save()

    def get_model(self):

        # # TODO : compare with from /proc/cpuinfo
        # with open('/proc/device-tree/model') as f:
            # model = f.read().strip('\x00')

        try:

            model = check_output('cat /proc/cpuinfo | grep "Model"', shell=True).decode('utf-8').split(':')[1].strip()

        except BaseException as e:

            logger.error(str(e))
            model = ''

        return model

    def get_serial(self):

        try:

            serial = check_output('cat /proc/cpuinfo | grep "Serial"', shell=True).decode('utf-8').split(':')[1].strip()

        except BaseException as e:

            logger.error(str(e))
            serial = ''

        return serial

    def get_revision(self):

        try:

            revision = check_output('cat /proc/cpuinfo | grep "Revision"', shell=True).decode('utf-8').split(':')[1].strip()

        except BaseException as e:

            logger.error(str(e))
            revision = ''

        return revision

    def get_hostname(self):

        try:

            hostname = check_output('hostname', shell=True).decode('utf-8').strip()

        except BaseException as e:

            logger.error(str(e))
            hostname = ''

        return hostname

    def get_wifi_ssid(self):

        try:
            # wifi_ssid = check_output(['iwgetid', '-r']).decode('utf-8').strip()
            # wifi_ssid = check_output('nmcli d show wlan0 | grep "GENERAL.CONNECTION:"', shell=True).decode('utf-8').split()[1].split('/')[0]
            wifi_ssid = check_output('nmcli d show wlan0 | grep "GENERAL.CONNECTION:"', shell=True).decode('utf-8').split(':')[1].strip()

        except BaseException as e:

            logger.error(str(e))
            wifi_ssid = ''

        return wifi_ssid

    def get_ip_address(self, version='v4'):

        try:

            if version == 'v4':
                try:
                    ip = check_output('nmcli d show wlan0 | grep "IP4.ADDRESS\[1]:"', shell=True).decode('utf-8').split()[1].split('/')[0]
                except:
                    ip = 'XXX.XXX.XXX.XXX'
            elif version == 'v6':
                try:
                    ip = check_output('nmcli d show wlan0 | grep "IP6.ADDRESS\[1]:"', shell=True).decode('utf-8').split()[1].split('/')[0]
                except:
                    ip = 'XXX.XXX.XXX.XXX'

        except BaseException as e:

            logger.error(str(e))
            ip = 'XXX.XXX.XXX.XXX'

        return ip

    # def get_ram(self):

        # TODO RAM
        # https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#raspberry-pi-revision-codes
        # w = check_output(['cat', '/proc/device-tree/compatible']).decode('utf-8').strip().split('\0')
        # self.ram =

    def get_temperature(self):

        # https://github.com/gpiozero/gpiozero/blob/master/gpiozero/internal_devices.py#L215

        sensor_file = '/sys/class/thermal/thermal_zone0/temp'

        try:

            with open(sensor_file, 'r') as f:
                cpu_temperature = float(f.read().strip()) / 1000

        except BaseException as e:

            logger.error(str(e))
            cpu_temperature = 0.0

        return cpu_temperature

    def get_os_version(self):

        try :

            os_version = platform.freedesktop_os_release().get('PRETTY_NAME', 'Linux')

        except BaseException as e:

            logger.error(str(e))
            os_version = ''

        return os_version

    def get_arch_version(self):

        try:

            if 'aarch64' in check_output('uname -m', shell=True).decode('utf-8').strip():
                arch_version = '64-bit'
            else:
                arch_version = '32-bit'

        except BaseException as e:

            logger.error(str(e))
            arch_version = ''

        return arch_version

    def get_wifi_power_save(self):

        try:

            if 'on' in check_output('/usr/sbin/iw wlan0 get power_save', shell=True).decode('utf-8').strip():
                power_save = True
            else:
                power_save = False

        except BaseException as e:

            logger.error(str(e))
            power_save = None

        return power_save

    def __str__(self):

        s = 'Raspberry Pi\n'
        s += '  Model: ' + self.model + '\n'
        s += '  Revision: ' + self.revision + '\n'
        s += '  Serial: ' + self.serial + '\n'
        s += '  OS version: ' + self.os_version + '\n'
        s += '  Arch version: ' + self.arch_version + '\n'
        s += '  Hostname: ' + self.hostname + '\n'
        # s += '  pigpio support: ' + 'yes\n' if self.pigpio_supported else 'no\n'
        s += '  CPU Temperature: ' + f'{self.get_temperature():.2f}' + '\n'
        s += '  WiFi: ' + self.wifi_ssid + '\n'
        s += '  IP address: ' + self.ip_address + '\n'
        s += f'  WiFi power save mode: {self.wifi_power_save}\n'


        return s

if __name__ == '__main__':

    rpi = Rpi()

    print(rpi)


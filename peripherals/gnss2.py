#! /usr/bin/python3

import os
import sys
from serial import Serial
import serial.tools.list_ports
import logging

from time import time
from datetime import datetime

sys.path.append('..')

from globals_parameters import LOGS_DESKTOP_FOLDER, TODAY

this_script = os.path.basename(__file__)[:-3]

today_log_path = os.path.join(LOGS_DESKTOP_FOLDER, TODAY)
if not os.path.exists(today_log_path):
    os.mkdir(today_log_path)

logger = logging.getLogger('entomoscope_gnss')
filename = os.path.join(today_log_path, TODAY + '_' + this_script + '.log')
file_handler = logging.FileHandler(filename, mode="a", encoding="utf-8")
logger.addHandler(file_handler)
formatter = logging.Formatter('%(asctime)s;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
file_handler.setFormatter(formatter)
logger.setLevel("DEBUG")

class Gnss2():

    def __init__(self, port=None):

        self.serial = Serial(baudrate=115200)
        self.is_opened = False
        self.port = None
        self.available = self.find()

        self.data = {'date': [0,0,0],
                    'time': [0,0,0],
                    'latitude': 0.0,
                    'ns': 'X',
                    'longitude': 0.0,
                    'ew': 'X',
                    'position_indication': 0,
                    'satellites_used': 0,
                    'hdop': 0.0,
                    'altitude': 0.0,
                    'last_upate': ''
                    }

        self.data_ready = False
        self.time = [0,0,0]

    def start(self):

        try:
            if self.available and not self.is_opened:
                self.serial.port = self.port
                self.serial.open()
                self.is_opened = True
        except BaseException as e:
            logger.error(str(e))

    def stop(self):

        try:
            if self.available and self.is_opened:
                self.serial.close()
                self.is_opened = False
        except BaseException as e:
            logger.error(str(e))

    def find(self):

        gnss_found = False

        ports = serial.tools.list_ports.comports()

        for port, desc, hwid in sorted(ports):
            if desc.startswith('u-blox 7 - GPS/GNSS Receiver'):
                gnss_found = True
                self.port = port
                break

        return gnss_found


    def get_data(self, duration):

        now = time()

        self.data_ready = False

        while time() - now < duration:

            n = self.serial.in_waiting

            if n > 0:

                try:

                    bytes_read = self.serial.read(n)
                    rx_buffer = bytes_read.decode('utf-8')

                    if rx_buffer.startswith('$GPRMC'):

                        # $GPRMC,124127.00,A,4337.15017,N,00119.40006,E,0.054,,020925,,,A*74

                        data = rx_buffer.split(',')

                        # ['$GPRMC', '124127.00', 'A', '4337.15017', 'N', '00119.40006', 'E', '0.054', '', '020925', '', '', 'A*74\r\n']

                        if len(data[9]) == 6:
                            self.data['date'] = [int(data[9][4:]), int(data[9][2:4]), int(data[9][0:2])]

                    elif rx_buffer.startswith('$GPGGA'):

                        # $GPGGA,124028.00,4337.15005,N,00119.40064,E,1,09,0.97,183.9,M,48.5,M,,*51

                        data = rx_buffer.split(',')

                        # ['$GPGGA', '134534.00', '', '', '', '', '0', '04', '27.08', '', '', '', '', '', '*6B\r\n']
                        # ['$GPGGA', '143433.00', '4337.14374', 'N', '00119.40799', 'E', '1', '07', '1.39', '179.1', 'M', '48.6', 'M', '', '*5A\r\n']

                        if data[1]:
                            self.data['time'] = [int(data[1][0:2]), int(data[1][2:4]), int(data[1][4:6])]
                        else:
                            self.data['time'] = [0, 0, 0]
                        if data[2]:
                            self.data['latitude'] = float(data[2][0:2]) + float(data[2][2:]) / 60
                        else:
                            self.data['latitude'] = 0.0
                        if data[3]:
                            self.data['ns'] = data[3]
                        else:
                            self.data['ns'] = 'X'
                        if data[4]:
                            self.data['longitude'] = float(data[4][0:3]) + float(data[4][3:]) / 60
                        else:
                            self.data['longitude'] = 0.0
                        if data[5]:
                            self.data['ew'] = data[5]
                        else:
                            self.data['ew'] = 'X'
                        if data[6]:
                            self.data['position_indication'] = int(data[6])
                        else:
                            self.data['position_indication'] = 0
                        if data[7]:
                            self.data['satellites_used'] = int(data[7])
                        else:
                            self.data['satellites_used'] = 0
                        if data[8]:
                            self.data['hdop'] = float(data[8])
                        else:
                            self.data['hdop'] = 0.0
                        if data[9]:
                            self.data['altitude'] = float(data[9])
                        else:
                            self.data['altitude'] = 0.0

                        self.data['last_update'] = datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')

                    self.data_ready = True

                except BaseException as e:

                    logger.error(str(e))

    def get_position(self):

        return self.data['latitude'], self.data['ns'], self.data['longitude'], self.data['ew'], self.data['altitude'], self.data['last_update'], self.data['satellites_used']

    def __str__(self):

        s = 'GNSS\n'

        s += f'  Available: {self.available}\n'

        s += f'  Data ready: {self.data_ready }\n'
        s += f"  Date: {2000 + self.data['date'][0]:02d}-{self.data['date'][1]:02d}-{self.data['date'][2]:02d}\n"
        s += f"  Time: {self.data['time'][0]:02d}:{self.data['time'][1]:02d}:{self.data['time'][2]:02d}\n"
        s += f"  Latitude: {self.data['latitude']:.6f} {self.data['ns']}\n"
        s += f"  Longitude: {self.data['longitude']:.6f}  {self.data['ew']}\n"
        s += f"  Position indication: {self.data['position_indication']}\n"
        s += f"  Satellites Used: {self.data['satellites_used']}\n"
        s += f"  Horizontal Precision: {self.data['hdop']}\n"
        s += f"  Altitude: {self.data['altitude']}\n"

        return s


if __name__ == '__main__':

    gnss = Gnss2()

    if gnss.available:

        gnss.start()

        gnss.get_data(2)

        gnss.stop()

        print(gnss)


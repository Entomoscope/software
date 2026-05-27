#! /usr/bin/python3

import os
from shutil import copyfile
from json import load, dump

from globals_parameters import TODAY, LOGS_DESKTOP_FOLDER

import logging
from logging.handlers import RotatingFileHandler

DEFAULT_CONFIGURATION_FILE = 'configuration2.json'

this_script = os.path.basename(__file__)[:-3]

today_log_path = os.path.join(LOGS_DESKTOP_FOLDER, TODAY)
if not os.path.exists(today_log_path):
    os.mkdir(today_log_path)

logger = logging.getLogger('entomoscope_configuration')
filename = os.path.join(today_log_path, TODAY + '_' + this_script + '.log')
file_handler = RotatingFileHandler(filename, mode="a", maxBytes=10000, backupCount=100, encoding="utf-8")
logger.addHandler(file_handler)
formatter = logging.Formatter('%(asctime)s.%(msecs)03d;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
file_handler.setFormatter(formatter)
logger.setLevel("DEBUG")

class Configuration2():

    _attributes = {'ai_detection', 'camera', 'cooling_system', 'ephemeris', 'files', 'gnss', 'images_capture', 'laser', 'leds', 'microphone', 'mode', 'environmental_monitoring', 'schedule', 'site', 'server', 'sounds_capture', 'wifi'}

    def __init__(self, configuration_file=DEFAULT_CONFIGURATION_FILE):

        self.configuration = None

        self.configurations_path = os.path.abspath(os.path.dirname(__file__))

        self.configuration_file = os.path.join(self.configurations_path, configuration_file)

        if not os.path.isfile(self.configuration_file):
            logger.warning('No configuration file found, create default one.')
            self.create_configuration_file()

        self.read()

    def read(self):

        try:

            with open(self.configuration_file, 'r') as f:
                self.configuration = load(f)

            for attr in self._attributes:
                setattr(self, attr, self.configuration[attr])

        except FileNotFoundError as e:

            logger.error('No configuration file found')

        except BaseException as e:

            logger.error(str(e))

    def save(self):

        try:

            with open(self.configuration_file, 'w') as f:
                dump(self.configuration, f, indent=4, sort_keys=True, separators=(',', ': '))

        except BaseException as e:

            logger.error(str(e))

    def create_configuration_file(self):

        setattr(self, 'ai_detection', {
                        'enable': False,
                        'file': '',
                        'image_height': 448,
                        "image_scale": 15.0,
                        'image_width': 704,
                        'min_confidence': 0.8
                        })

        setattr(self, 'camera', {
                        'autofocus': {
                            'enable': True,
                            'lens_position': 8.5,
                            'measure_enable': False,
                            'measure_mode': 'laplacian',
                            'mode': 'Manual',
                            'range': 'Normal',
                            'speed': 'Normal'
                        },
                        'auto_exposure_gain': {
                            'analogue_gain': 1,
                            "enable": True,
                            'mode': 'Auto',
                            'exposure_mode': 'Normal',
                            'exposure_time': 10000,
                            'exposure_value': 0.0,
                            'flicker_mode': 'Off',
                            'flicker_period': 10000
                        },
                        'image_adjustments': {
                            'brightness': 0.0,
                            'contrast': 1.0,
                            'saturation': 1.0,
                            'sharpness': 1.0
                        },
                        'image_height': 2592,
                        'image_width': 4608,
                        'model': 'v3',
                        'sensor': {
                            'capture_mode': 2,
                            'crop_limits': [0, 0, 4608, 2592],
                            'height_preview': 1080,
                            'preview_mode': 2,
                            'width_preview': 1920,
                            'resolution': [4608, 2592]
                        },
                        'auto_white_balance': {
                            'enable': True,
                            'mode': 'Auto'
                        }})

        setattr(self, 'cooling_system', {
                            'cpu_temperature_check_interval': 2,
                            'cpu_temperature_levels': [65, 70, 75, 80],
                            'enable': True,
                            'fan_speed_levels': [25, 50, 75, 100]
                        })

        setattr(self, 'environmental_monitoring', {
                            'enable': True,
                            'time_step': 5
                        })

        setattr(self, 'ephemeris', {
                            'location': ''
                        })

        setattr(self, 'files', {
                            'jpeg_quality': 100
                        })

        setattr(self, 'gnss', {
                            'altitude': 0.0,
                            'enable': True,
                            'latitude': '',
                            'last_update': '',
                            'last_update_dop': 0.0,
                            'longitude': '',
                            'mode': 'auto',
                            'satellites_used': 0
                        })

        setattr(self, 'images_capture', {
                            'enable': False,
                            'fast_mode': False,
                            'multifocus': {
                                'enable': False,
                                'lens_position_offset': 0
                            },
                            'time_step': 5
                        })

        setattr(self, 'laser', {
                            'enable': False,
                        })

        setattr(self, 'leds', {
                            'always_on': False,
                            'delay_off': 0,
                            'delay_on': 0,
                            'intensity_front': 0,
                            'intensity_rear_deported_uv': 0
                        })

        setattr(self, 'microphone', {
                            'gain': 2,
                            'sample_rate': 48000
                        })

        setattr(self, 'mode', {
                            'mode': 'trap'
                        })

        setattr(self, 'schedule', {
                            'enable': False,
                            'next_startup': '2026-05-01 07:00',
                            'next_shutdown': '2026-05-01 18:00',
                            'off_duration': 60,
                            'on_duration': 60,
                            'periodicity': 'every_day'
                        })

        setattr(self, 'server', {
                            'image_constraints': {
                                'centered': False,
                                'square': False
                            },
                            'preview_size': {
                                'max_width': 800
                            }
                        })

        setattr(self, 'site', {
                            'id': '',
                        })

        setattr(self, 'sounds_capture', {
                            'enable': False,
                            'duration': 60
                        })

        setattr(self, 'wifi', {
                            'station_ssid': ''
                        })

        self.configuration = {key: None for key in self._attributes}

        for attr in self._attributes:
            self.configuration[attr] = getattr(self, attr)

        self.save()

    def get(self):

        return self.configuration

    def copy_to(self, copy_path):

        try:

            copyfile(self.configuration_file, copy_path)

            success = True

        except OSError as e:

            logger(str(e))

            success = False

    def to_string(self):

        s = ''

        for attr in sorted(self._attributes):

            d = getattr(self, attr)

            s += ' ' + attr.replace('_', ' ').capitalize() + '\n'
            for key, value in d.items():
                if type(value) == dict:
                    s += f"   {key.replace('_', ' ').capitalize()}\n"
                    for subkey, subvalue in value.items():
                        if type(subvalue) == dict:
                            s += f"     {subkey.replace('_', ' ').capitalize()}\n"
                        else:
                            s += f"     {subkey.replace('_', ' ').capitalize()}: {subvalue}\n"
                else:
                    s += f"   {key.replace('_', ' ').capitalize()}: {value}\n"

        return s

    def __str__(self):

        s = self.to_string()

        return s

if __name__ == '__main__':

    configuration = Configuration2()

    print(configuration)

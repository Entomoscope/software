#! /usr/bin/python3

import os
from shutil import copyfile
from json import load, dump

DEFAULT_CONFIGURATION_FILE = 'configuration2.json'

class Configuration2():

    _attributes = {'ai_detection', 'camera', 'cooling_system', 'ephemeris', 'files', 'gnss', 'images_capture', 'laser', 'leds', 'microphone', 'monitor_environment', 'schedule', 'site', 'server', 'sounds_capture'}

    def __init__(self, configuration_file=DEFAULT_CONFIGURATION_FILE):

        self.configuration = None

        self.configurations_path = os.path.abspath(os.path.dirname(__file__))

        self.configuration_file = os.path.join(self.configurations_path, configuration_file)

        if not os.path.isfile(self.configuration_file):
            self.create_configuration_file()

        self.read()

    def read(self):

        with open(self.configuration_file, 'r') as f:
            self.configuration = load(f)

        for attr in self._attributes:
            setattr(self, attr, self.configuration[attr])

    def save(self):

        with open(self.configuration_file, 'w') as f:
            dump(self.configuration, f, indent=4, sort_keys=True, separators=(',', ': '))

    def create_configuration_file(self):

        setattr(self, 'ai_detection', {
                        'enable': False,
                        'min_confidence': 0.8,
                        'image_height': 320,
                        "image_scale": 1.0,
                        'image_width': 320
                        })

        setattr(self, 'camera', {
                        'autofocus': {
                            'enable': True,
                            'lens_position': 8.5,
                            'mode': 'Manual',
                            'range': 'Normal',
                            'speed': 'Normal'
                        },
                        'auto_exposure_gain': {
                            'analogue_gain': 1,
                            "enable": True,
                            'mode': 'Manual',
                            'exposure_mode': 'Normal',
                            'exposure_time': 2000,
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
                        'image_height': 1900,
                        'image_width': 1900,

                        'model': 'v3',
                        'sensor': {
                            'crop_limits': [1285, 390, 1900, 1900],
                            'mode': 2
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

        setattr(self, 'ephemeris', {
                            'location': ''
                        })

        setattr(self, 'files', {
                            'jpeg_quality': 95
                        })

        setattr(self, 'gnss', {
                            'altitude': 0.0,
                            'enable': True,
                            'latitude': 0.0,
                            'last_update': '',
                            'last_update_dop': 0.0,
                            'longitude': 0.0,
                            'mode': 'auto',
                            'satellites_used': 0
                        })

        setattr(self, 'images_capture', {
                            'enable': False,
                            'mode': 'trap',
                            'time_step': 5
                        })

        setattr(self, 'laser', {
                            'enable': False,
                        })

        setattr(self, 'leds', {
                            'delay_off': 0,
                            'delay_on': 0,
                            'intensity_front': 0,
                            'intensity_rear_deported_uv': 90
                        })

        setattr(self, 'microphone', {
                            "sample_rate": 44100
                        })

        setattr(self, 'monitor_environment', {
                            'enable': True,
                            'time_step': 300
                        })

        setattr(self, 'schedule', {
                            'enable': False,
                            'off_duration': 1,
                            'on_duration': 1,
                            'next_startup': '2025-01-01 07:00',
                            'next_shutdown': '2025-01-01 18:00',
                        })

        setattr(self, 'server', {
                            'image_constraints': {
                                'square': False,
                                'centered': False
                            },
                            'preview_size': {
                                'max_width': 800
                            }
                        })

        setattr(self, 'site', {
                            'id': '',
                        })

        setattr(self, 'sounds_capture', {
                            'duration': 3,
                            'enable': False
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

            print(str(e))

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

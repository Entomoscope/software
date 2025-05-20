import os
from json import load, dump

class Configuration():

    _attributes = {'ai_detection', 'camera', 'files', 'gnss', 'images_capture', 'laser', 'leds', 'monitor_environment', 'schedule', 'site', 'sounds_capture'}

    def __init__(self):

        self.configuration = None

        self.configurations_path = os.path.abspath(os.path.dirname(__file__))

        self.configuration_file = os.path.join(self.configurations_path, 'configuration.json')

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
                        'enable': True,
                        'min_confidence': 0.8,
                        'image_height': 320,
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
                        'exposure_gain': {
                            'analog_gain': 1.5,
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
                        'white_balance': {
                            'enable': True,
                            'mode': 'Auto'
                        }})

        setattr(self, 'files', {
                            'jpeg_quality': 95
                        })

        setattr(self, 'gnss', {
                            'enable': True,
                            'latitude': 0.0,
                            'last_update': 0,
                            'last_update_dop': 0.0,
                            'last_update_num_satellites': 0,
                            'longitude': 0.0,
                            'mode': 'auto'
                        })

        setattr(self, 'images_capture', {
                            'enable': True,
                            'time_step': 5
                        })

        setattr(self, 'laser', {
                            'enable': False,
                        })

        setattr(self, 'leds', {
                            'intensity_deported': 0,
                            'intensity_front': 90,
                            'intensity_rear': 35,
                            'intensity_uv': 0,
                            'mode': 1
                        })

        setattr(self, 'monitor_environment', {
                            'enable': True,
                            'time_step': 300
                        })

        setattr(self, 'schedule', {
                            'enable': True,
                            'off_duration': 1,
                            'on_duration': 1,
                            'sleep': '18:00',
                            'wakeup': '07:00'
                        })

        setattr(self, 'site', {
                            'id': 'XX',
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

    configuration = Configuration()

    print(configuration)

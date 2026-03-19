import os
import sys

from time import sleep, time

import logging
from logging.handlers import RotatingFileHandler

import pigpio

from math import exp

# Execute the following command to execute pigpiod at startup:
# sudo systemctl enable pigpiod
# To run pigpiod once:
# sudo systemctl start pigpiod
# Source: https://gpiozero.readthedocs.io/en/stable/remote_gpio.html

sys.path.append('..')

from globals_parameters import LOGS_DESKTOP_FOLDER, TODAY

this_script = os.path.basename(__file__)[:-3]

today_log_path = os.path.join(LOGS_DESKTOP_FOLDER, TODAY)
if not os.path.exists(today_log_path):
    os.mkdir(today_log_path)

logger = logging.getLogger('entomoscope_leds')
filename = os.path.join(today_log_path, TODAY + '_' + this_script + '.log')
file_handler = RotatingFileHandler(filename, mode="a", maxBytes=10000, backupCount=100, encoding="utf-8")
logger.addHandler(file_handler)
formatter = logging.Formatter('%(asctime)s.%(msecs)03d;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
file_handler.setFormatter(formatter)
logger.setLevel("DEBUG")

class Leds():

    pwm_frequency = 10000
    # num_dimming_levels = 256
    # dimming_levels = list(range(0, num_dimming_levels))
    # max_dimming_level = dimming_levels[-1]

    def __init__(self, pin, intensity=0):

        self.pin = pin

        self.pi = pigpio.pi()

        self.pi.set_PWM_range(self.pin, 100)
        self.pi.set_PWM_frequency(self.pin, self.pwm_frequency)
        self.pi.set_PWM_dutycycle(self.pin, 0)

        # linear_dimming_curve = [x/self.max_dimming_level for x in self.dimming_levels]
        # square_dimming_curve = [x*x/(self.max_dimming_level*self.max_dimming_level) for x in self.dimming_levels]
        # # https://en.wikipedia.org/wiki/Logistic_function
        # scurve_dimming_curve = [0.0]
        # scurve_dimming_curve.extend([1 / (1 + exp( (-1/25) * (x - num_dimming_levels/2))) for x in dimming_levels[1:-1]])
        # scurve_dimming_curve.append(1.0)
        # # # https://www.kgp-electronics.de/downloads/led-driver/cc-linear/LC115W200-500_DALI/Data_Sheet/LC115W200-500_DALI.pdf
        # # dali_dimming_curve = [pow(10, (x-1)/(253/3)-1 for x in dimming_levels];

        # self.dimming_curve = [0.0]
        # self.dimming_curve.extend([1 / (1 + exp( (-1/25) * (x - self.num_dimming_levels/2))) for x in self.dimming_levels[1:-1]])
        # self.dimming_curve.append(1.0)

        self.is_on = False

        self.pwm = 0

        self.intensity = intensity

        self.set_intensity(intensity)

    def set_pwm(self, pwm):

        self.led.value = pwm

    def set_intensity(self, intensity):

        if intensity >= 0 and intensity <= 100:

            self.intensity = intensity

            self.pwm = intensity

            # value = self.intensity  / 100 * self.max_dimming_level
            # for dimming_level in self.dimming_levels:
                # if dimming_level >= value:
                    # self.pwm = int(100*self.dimming_curve[dimming_level])
                    # break

            logger.info(f'set intensity to {intensity} % (pin {self.pin})')

            if self.is_on:
                self.turn_on()

    def turn_on(self):

        try:

            self.pi.set_PWM_dutycycle(self.pin, self.pwm)

            # logger.info(f'leds on (pin {self.pin})')

            self.is_on = True

        except BaseException as e:

            logger.error(str(e))

    def turn_off(self):

        if self.is_on:

            try:

                self.pi.set_PWM_dutycycle(self.pin, 0)

                # logger.info(f'leds off (pin {self.pin})')

                self.is_on = False

            except BaseException as e:

                logger.error(str(e))

if __name__ == '__main__':

    leds = [Leds(23, intensity=0), Leds(24, intensity=0)]

    # print(leds[-1].dimming_levels)

    for led in leds:

        # led.set_intensity(50)

        led.turn_on()

    for i in range(0, 100, 10):

        for led in leds:
            led.set_intensity(i)

        print(f'{i:03d}%')
        sleep(1)

    for led in leds:

        led.turn_off()


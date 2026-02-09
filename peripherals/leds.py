from time import sleep, time

import pigpio

from math import exp

# Execute the following command to execute pigpiod at startup:
# sudo systemctl enable pigpiod
# To run pigpiod once:
# sudo systemctl start pigpiod
# Source: https://gpiozero.readthedocs.io/en/stable/remote_gpio.html

class Leds():

    pwm_frequency = 20000
    num_dimming_levels = 256
    dimming_levels = list(range(0, num_dimming_levels))
    max_dimming_level = dimming_levels[-1]

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

        self.dimming_curve = [0.0]
        self.dimming_curve.extend([1 / (1 + exp( (-1/25) * (x - self.num_dimming_levels/2))) for x in self.dimming_levels[1:-1]])
        self.dimming_curve.append(1.0)

        self.is_on = False

        self.intensity = intensity

        self.set_intensity(intensity)

    def set_pwm(self, pwm):

        self.led.value = pwm

    def set_intensity(self, intensity):

        if intensity >= 0 and intensity <= 100:

            self.intensity = intensity

            if self.is_on:
                self.turn_on()

    def turn_on(self):

        value = self.intensity  / 100 * self.max_dimming_level

        for dimming_level in self.dimming_levels:
            if dimming_level >= value:
                pwm = self.dimming_curve[dimming_level]
                self.pi.set_PWM_dutycycle(self.pin, int(100*pwm))
                break

        self.is_on = True

    def turn_off(self):

        if self.is_on:

            self.pi.set_PWM_dutycycle(self.pin, 0)

            self.is_on = False

if __name__ == '__main__':

    leds = [Leds(23, intensity=0), Leds(24, intensity=0)]

    print(leds[-1].dimming_levels)

    for led in leds:

        led.turn_on()

    for i in range(0, 100, 10):

        for led in leds:
            led.set_intensity(i)

        print(f'{i:03d}%')
        sleep(1)

    for led in leds:

        led.turn_off()


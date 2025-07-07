import argparse
import pigpio
from gpiozero import CPUTemperature

from time import sleep

from pinout import FAN_PIN

# https://noctua.at/pub/media/wysiwyg/Noctua_PWM_specifications_white_paper.pdf
# Target frequency: 25kHz, acceptable range 21kHz to 28kHz
DEFAULT_FAN_PWM_FREQUENCY = 25000

class Fan:

    def __init__(self, pin=FAN_PIN, frequency=DEFAULT_FAN_PWM_FREQUENCY):

        self.pin = pin
        self.pwm = pigpio.pi()
        self.pwm.set_mode(self.pin, pigpio.OUTPUT)
        self.frequency = frequency
        self.pwm.set_PWM_frequency(self.pin, self.frequency)
        self.pwm.set_PWM_range(self.pin, 100)
        self.set_speed(0)

    def set_speed(self, speed):

        if speed >= 0 and speed <= 100:
            self.dutycycle = speed
            self.pwm.set_PWM_dutycycle(self.pin, int(self.dutycycle))
            
    def get_speed(self):
    
        return self.dutycycle

    def test(self):

        for i in range(0, 101, 10):            
            self.set_speed(i)
            print(f'Fan speed: {self.get_speed()}%')
            sleep(2)
        self.set_speed(0)
        print(f'Fan speed: {self.get_speed()}%')


def main(args):

    fan = Fan()

    if args.low_speed:   
        fan.set_speed(20)
    elif args.mid_speed:
        fan.set_speed(50)
    elif args.high_speed:
        fan.set_speed(100)
    elif args.stop:
        fan.set_speed(0)
    elif args.test:
        fan.test()

if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog='fan.py')

    parser.add_argument('-ls', '--low_speed', help='Low speed',
                        required=False, action='store_true')
    parser.add_argument('-ms', '--mid_speed', help='Mid speed',
                        required=False, action='store_true')
    parser.add_argument('-hs', '--high_speed', help='High speed',
                        required=False, action='store_true')
    parser.add_argument('-s', '--stop', help='Stop',
                        required=False, action='store_true')
    parser.add_argument('-t', '--test', help='Test',
                        required=False, action='store_true')

    args = parser.parse_args()
    
    main(args)

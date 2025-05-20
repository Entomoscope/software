import pigpio
from time import sleep

from peripherals.pinout import SHUTDOWN_PIN
from globals_parameters import DELAY_BEFORE_SHUTDOWN

if __name__ == '__main__':

    pi.write(SHUTDOWN_PIN, 1)

    sleep(DELAY_BEFORE_SHUTDOWN)

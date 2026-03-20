import sys
import os
import smbus
from subprocess import check_output, CalledProcessError
from time import sleep

import logging
from logging.handlers import RotatingFileHandler

sys.path.append('..')

from globals_parameters import LOGS_DESKTOP_FOLDER, TODAY

this_script = os.path.basename(__file__)[:-3]

today_log_path = os.path.join(LOGS_DESKTOP_FOLDER, TODAY)
if not os.path.exists(today_log_path):
    os.mkdir(today_log_path)

logger = logging.getLogger('entomoscope_wittypi')
filename = os.path.join(today_log_path, TODAY + '_' + this_script + '_ento.log')
file_handler = RotatingFileHandler(filename, mode="a", maxBytes=50000, backupCount=100, encoding="utf-8")
logger.addHandler(file_handler)
formatter = logging.Formatter('%(asctime)s.%(msecs)03d;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
file_handler.setFormatter(formatter)
logger.setLevel("DEBUG")

DIODE_VOLTAGE_DROP_OUT = 0.5

class WittyPi():

    I2C_ADDRESS = 0x08
    I2C_ADDRESS_STR = f'{I2C_ADDRESS:02X}'

    NONE = 0
    ALARM_STARTUP = 1
    ALARM_SHUTDOWN = 2
    BUTTON_CLICKED = 3
    INPUT_VOLTAGE_TOO_LOW = 4
    INPUT_VOLTAGE_RESTORED = 5
    OVER_TEMPERATURE = 6
    BELOW_TEPERATURE = 7
    ALARM1_DELAYED = 8

    DO_NOTHING = 0
    SHUTDOWN = 1
    STARTUP = 2

    TEMPERATURE_MIN_THRESHOLD = -30
    TEMPERATURE_MAX_THRESHOLD = 80

    def __init__(self):

        try:

            self.i2c_bus = smbus.SMBus(1)
            self.available = self.detect()

        except PermissionError as e:

            self.available = False

            logger.error(str(e))

        if not self.available:
            logger.error('Witty Pi is not detected')

        self.date = ''

        self.firmware_id = 0
        self.input_voltage = 0.0
        self.output_voltage = 0.0
        self.power_mode = 0
        self.firmware_revision = 0

        self.startup_alarm = [-1, -1, -1, -1, -1]
        self.shutdown_alarm = [-1, -1, -1, -1, -1]

        self.low_voltage_threshold = 0.0
        self.recovery_voltage_threshold = 0.0

        self.below_temperature_action = 0
        self.below_temperature_threshold = 0

        self.over_temperature_action = 0
        self.over_temperature_threshold = 0

        self.led_pulse_interval = 0
        self.led_light_up_duration = 0

    def detect(self):

        try:

            output = check_output('/usr/sbin/i2cdetect -y 1', shell=True).decode('utf-8').split(' ')

            available = self.I2C_ADDRESS_STR in output

        except CalledProcessError as e:

            available = False

            logger.error(str(e))

        return available

    def set_date(self, year, month, day, hour, minute, second):

        if year > 2000:
            year -= 2000

        year_bcd = ((year // 10) << 4)+ (year - 10 * (year // 10))
        month_bcd = ((month // 10) << 4) + (month - 10 * (month // 10))
        day_bcd = ((day // 10) << 4) + (day - 10 * (day // 10))

        hour_bcd = ((hour // 10) << 4) + (hour - 10 * (hour // 10))
        minute_bcd = ((minute // 10) << 4) + (minute - 10 * (minute // 10))
        second_bcd = ((second // 10) << 4) + (second - 10 * (second // 10))

        success = self.write_register(58, second_bcd)

        success = self.write_register(59, minute_bcd)

        success = self.write_register(60, hour_bcd)

        success = self.write_register(61, day_bcd)

        success = self.write_register(62, 0)

        success = self.write_register(63, month_bcd)

        success = self.write_register(64, year_bcd)

        logger.info(f'date set to 20{year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}')

    def get_info(self):

        self.get_date()
        self.get_firmware_id()
        self.get_firmware_revision()
        self.get_input_voltage()
        self.get_output_voltage()
        self.get_output_current()
        self.get_power_mode()
        self.get_alarms()
        self.get_low_voltage_threshold()
        self.get_recovery_voltage_threshold()
        self.get_below_temperature()
        self.get_over_temperature()
        self.get_led_pulse_interval()
        self.get_led_light_up_duration()

    def get_date(self):

        self.year = self.read_register(64)
        self.year = ((self.year & 0b11110000) >> 4) * 10 + (self.year & 0b00001111)
        self.month = self.read_register(63)
        self.month = ((self.month & 0b11110000) >> 4) * 10 + (self.month & 0b00001111)
        self.day = self.read_register(61)
        self.day = ((self.day & 0b11110000) >> 4) * 10 + (self.day & 0b00001111)
        self.hour = self.read_register(60)
        self.hour = ((self.hour & 0b11110000) >> 4) * 10 + (self.hour & 0b00001111)
        self.minute = self.read_register(59)
        self.minute = ((self.minute & 0b11110000) >> 4) * 10 + (self.minute & 0b00001111)
        self.second = self.read_register(58) & 0b01111111 # line 217 in wittypi/utilities.sh
        self.second = ((self.second & 0b11110000) >> 4) * 10 + (self.second & 0b00001111)

        self.date = f'{self.year + 2000}-{self.month:02d}-{self.day:02d} {self.hour:02d}:{self.minute:02d}:{self.second:02d}'

        logger.info(f'date: {self.date}')

    def get_firmware_id(self):

        try:

            self.firmware_id = self.read_register(0)
            logger.info(f'firmware id: {self.firmware_id}')

        except BaseException as e:

            self.firmware_id = 0

    def get_input_voltage(self):

        try:

            self.input_voltage = self.read_register(1) + self.read_register(2) / 100
            self.input_voltage += DIODE_VOLTAGE_DROP_OUT
            logger.info(f'input voltage: {self.input_voltage}')

        except BaseException as e:

            self.input_voltage = 0.0

    def get_output_voltage(self):

        try:

            self.output_voltage = self.read_register(3) + self.read_register(4) / 100
            logger.info(f'output voltage: {self.output_voltage}')

        except BaseException as e:

            self.output_voltage = 0.0

    def get_output_current(self):

        try:

            self.output_current = self.read_register(5) + self.read_register(6) / 100
            logger.info(f'output current: {self.output_current}')

        except BaseException as e:

            self.output_current = 0.0

    def get_power_mode(self):

        try:

            self.power_mode = self.read_register(7)
            logger.info(f'power mode: {self.power_mode}')

        except BaseException as e:

            self.power_mode = 0

    def get_firmware_revision(self):

        try:

            self.firmware_revision = self.read_register(12)
            logger.info(f'firmware revision: {self.firmware_revision}')

        except BaseException as e:

            self.firmware_revision = 0

    def is_alarm_startup_triggered(self):

        return self.read_register(9)

    def is_alarm_shutdown_triggered(self):

        return self.read_register(10)

    def get_latest_action_reason_code(self):

        return self.read_register(11)

    def get_latest_action_reason(self):

        code = self.get_latest_action_reason_code()

        reasons  = ['N/A', 'ALARM1', 'ALARM2', 'button is clicked', 'input voltage too low', 'input voltage restored', 'over temperature', 'below temperature', 'ALARM1 delayed', 'USB 5V connected', 'power connected', 'reboot']

        if code >= 0 and code < len(reasons):

            return reasons[code]

        else:

            return f'unknown reason {code}'

    def get_startup_alarm(self):

        self.get_alarms()

        return self.startup_alarm

    def set_startup_alarm(self, day, hour, minute):

        success = False

        try:

            if day > 0 and day < 32 and hour >= 0 and hour <= 23 and minute >= 0 and minute < 60:

                day_bcd = ((day // 10) << 4)+ (day - 10 * (day // 10))
                hour_bcd = ((hour // 10) << 4) + (hour - 10 * (hour // 10))
                minute_bcd = ((minute // 10) << 4) + (minute - 10 * (minute // 10))

                success = self.write_register(27, 0)

                success = self.write_register(28, minute_bcd)

                success = self.write_register(29, hour_bcd)

                success = self.write_register(30, day_bcd)

                logger.info(f'startup alarm set to {day:02d} {hour:02d}:{minute:02d}')

        except BaseException as e:

            logger.error(str(e))

        return success

    def get_shutdown_alarm(self):

        self.get_alarms()

        return self.shutdown_alarm

    def set_shutdown_alarm(self, day, hour, minute):

        success = False

        if day > 0 and day < 32 and hour >= 0 and hour <= 23 and minute >= 0 and minute < 60:

            day_bcd = ((day // 10) << 4)+ (day - 10 * (day // 10))
            hour_bcd = ((hour // 10) << 4) + (hour - 10 * (hour // 10))
            minute_bcd = ((minute // 10) << 4) + (minute - 10 * (minute // 10))

            success = self.write_register(32, 0)

            success = self.write_register(33, minute_bcd)

            success = self.write_register(34, hour_bcd)

            success = self.write_register(35, day_bcd)

            logger.info(f'shutdown alarm set to {day:02d} {hour:02d}:{minute:02d}')

        return success

    def get_alarms(self):

        try:

            self.startup_alarm[0] = self.read_register(27) # Seconds
            self.startup_alarm[1] = self.read_register(28) # Minutes
            self.startup_alarm[2] = self.read_register(29) # Hours
            self.startup_alarm[3] = self.read_register(30) # Day
            self.startup_alarm[4] = self.read_register(31) # Weekday

            self.shutdown_alarm[0] = self.read_register(32) # Seconds
            self.shutdown_alarm[1] = self.read_register(33) # Minutes
            self.shutdown_alarm[2] = self.read_register(34) # Hours
            self.shutdown_alarm[3] = self.read_register(35) # Day
            self.shutdown_alarm[4] = self.read_register(36) # Weekday

            for i in range(0, 5):

                self.startup_alarm[i] = ((self.startup_alarm[i] & 0b11110000) >> 4) * 10 + (self.startup_alarm[i] & 0b00001111)
                self.shutdown_alarm[i] = ((self.shutdown_alarm[i] & 0b11110000) >> 4) * 10 + (self.shutdown_alarm[i] & 0b00001111)

        except BaseException as e:

            logger.error(str(e))

            self.startup_alarm = [-1, -1, -1, -1, -1]
            self.shutdown_alarm = [-1, -1, -1, -1, -1]

    def set_below_temperature(self, action, threshold):

        success = False

        if threshold >= TEMPERATURE_MIN_THRESHOLD and threshold <= TEMPERATURE_MAX_THRESHOLD and action in [0, 1, 2]:

            success = self.write_register(43, action)
            success = self.write_register(44, threshold)

            logger.info(f'below temperature set to {threshold} and action set to {action}')

        return success

    def get_below_temperature(self):

        self.below_temperature_action = self.read_register(43)
        self.below_temperature_threshold = self.read_register(44)

    def set_over_temperature(self, action, threshold):

        success = False

        if threshold >= TEMPERATURE_MIN_THRESHOLD and threshold <= TEMPERATURE_MAX_THRESHOLD and action in [0, 1, 2]:

            success = self.write_register(45, action)
            success = self.write_register(46, threshold)

            logger.info(f'over temperature set to {threshold} and action set to {action}')

        return success

    def get_over_temperature(self):

        self.over_temperature_action = self.read_register(45)
        self.over_temperature_threshold = self.read_register(46)

    def set_led_pulse_interval(self, interval):

        try:

            interval = int(interval)

            if interval > 0 and interval < 255:

                success = self.write_register(18, interval)

                logger.info(f'led pulse interval set to {interval} seconds')

        except BaseException as e:

            logger.error(str(e))

    def get_led_pulse_interval(self):

        self.led_pulse_interval = self.read_register(18)

    def set_led_light_up_duration(self, duration):

        try:

            duration = int(duration)

            if duration > 0 and duration < 255:

                success = self.write_register(20, duration)

                logger.info(f'led light up duration set to {duration} milliseconds')

        except BaseException as e:

            logger.error(str(e))

    def get_led_light_up_duration(self):

        self.led_light_up_duration = self.read_register(20)

    def set_low_voltage_threshold(self, voltage):

        if voltage >= 2.0 and voltage <= 25.0:
            success = self.write_register(19, int(voltage*10))
            logger.info(f'low voltage threshold set to {voltage} volts')
        else:
            logger.error(f'low voltage threshold {voltage} not set. Must be in the range [2.0 25.0]')

    def get_low_voltage_threshold(self):

        self.low_voltage_threshold = self.read_register(19) / 10

    def set_recovery_voltage_threshold(self, voltage):

        if voltage >= 2.0 and voltage <= 25.0:
            success = self.write_register(22, int(voltage*10))
            logger.info(f'recovery voltage threshold set to {voltage} volts')
        else:
            logger.error(f'recovery voltage threshold {voltage} not set. Must be in the range [2.0 25.0]')

    def get_recovery_voltage_threshold(self):

        self.recovery_voltage_threshold = self.read_register(22) / 10

    def read_register(self, register):

        try:

            data = self.i2c_bus.read_byte_data(self.I2C_ADDRESS, register)

        except OSError as e:

            logger.error(f'error reading register 0x{register:02X}')
            logger.error(str(e))
            data = None

        return data

    def write_register(self, register, value):

        try:

            self.i2c_bus.write_byte_data(self.I2C_ADDRESS, register, value)

            success = True

        except OSError as e:

            logger.error(f'error writing {value} to register 0x{register:02X}')
            logger.error(str(e))

            success = False

        return success

    def __str__(self):

        s = 'Witty Pi\n'

        s += f'  Firmware ID: {self.firmware_id:02X}\n'
        s += f'  Firmware revision: {self.firmware_revision}\n'
        s += f'  Date: {self.date}\n'
        s += f'  Input voltage: {self.input_voltage:.3f}V\n'
        s += f'  Output voltage: {self.output_voltage:.3f}V\n'
        s += f'  Output current: {self.output_current:.3f}A\n'
        s += '  Power mode: ' + ('LDO regulator' if self.power_mode == 1 else '5V USB') + '\n'
        s += f'  Startup alarm: {self.startup_alarm[3]:02d} {self.startup_alarm[2]:02d}:{self.startup_alarm[1]:02d}:{self.startup_alarm[0]:02d}\n'
        s += f'  Shutdown alarm: {self.shutdown_alarm[3]:02d} {self.shutdown_alarm[2]:02d}:{self.shutdown_alarm[1]:02d}:{self.shutdown_alarm[0]:02d}\n'
        if self.low_voltage_threshold == 0 or self.low_voltage_threshold == 25.5:
            s += f'  Low voltage threshold: disable\n'
        else:
            s += f'  Low voltage threshold: {self.low_voltage_threshold:.1f}V\n'
        if self.recovery_voltage_threshold == 0 or self.recovery_voltage_threshold == 25.5:
            s += f'  Recovery voltage threshold: disable\n'
        else:
            s += f'  Recovery voltage threshold: {self.recovery_voltage_threshold:.1f}V\n'
        s += f'  Below temperature threshold: {self.below_temperature_threshold} C\n'
        if self.below_temperature_action == 0:
            s += f'  Below temperature action: do nothing\n'
        elif self.below_temperature_action == 1:
            s += f'  Below temperature action: shutdown\n'
        elif self.below_temperature_action == 2:
            s += f'  Below temperature action: startup\n'
        s += f'  Over temperature threshold: {self.over_temperature_threshold} C\n'
        if self.below_temperature_action == 0:
            s += f'  Over temperature action: do nothing\n'
        elif self.below_temperature_action == 1:
            s += f'  Over temperature action: shutdown\n'
        elif self.below_temperature_action == 2:
            s += f'  Over temperature action: startup\n'
        s += f'  LED pulse interval: {self.led_pulse_interval}\n'
        s += f'  LED light up duration: {self.led_light_up_duration}\n'

        return s

def main():

    witty_pi = WittyPi()

    witty_pi.set_low_voltage_threshold(10.5)

    if witty_pi.available:

        witty_pi.get_info()

        # witty_pi.set_startup_alarm(14, 16, 39)
        # witty_pi.set_shutdown_alarm(14, 16, 37)

        print(witty_pi)

        # for i in range(0,50):
            # witty_pi.get_output_current()
            # print(f'{witty_pi.output_current:.3f} ', end='')
            # sleep(0.1)

if __name__ == '__main__':

    main()

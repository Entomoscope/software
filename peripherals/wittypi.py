import sys
import os
import smbus
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
formatter = logging.Formatter('%(asctime)s;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
file_handler.setFormatter(formatter)
logger.setLevel("DEBUG")

DIODE_VOLTAGE_DROP_OUT = 0.5

class WittyPi():

    I2C_ADDRESS = 0x08

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

        self.i2c_bus = smbus.SMBus(1)

        self.date = ''

        self.firmware_id = 0
        self.input_voltage = 0.0
        self.output_voltage = 0.0
        self.power_mode = 0
        self.firmware_revision = 0

        self.startup_alarm = [-1, -1, -1, -1, -1]
        self.shutdown_alarm = [-1, -1, -1, -1, -1]

        self.below_temperature_action = 0
        self.below_temperature_threshold = 0

        self.over_temperature_action = 0
        self.over_temperature_threshold = 0

        self.led_pulse_interval = 0
        self.led_light_up_duration = 0

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
        self.get_input_voltage()
        self.get_output_voltage()
        self.get_output_current()
        self.get_power_mode()
        self.get_firmware_revision()
        self.get_alarms()
        self.get_below_temperature()
        self.get_over_temperature()
        self.get_led_pulse_interval()
        self.get_led_light_up_duration()

    def get_date(self):

        year = self.read_register(64)
        year = ((year & 0b11110000) >> 4) * 10 + (year & 0b00001111)
        month = self.read_register(63)
        month = ((month & 0b11110000) >> 4) * 10 + (month & 0b00001111)
        day = self.read_register(61)
        day = ((day & 0b11110000) >> 4) * 10 + (day & 0b00001111)
        hour = self.read_register(60)
        hour = ((hour & 0b11110000) >> 4) * 10 + (hour & 0b00001111)
        minute = self.read_register(59)
        minute = ((minute & 0b11110000) >> 4) * 10 + (minute & 0b00001111)
        second = self.read_register(58)
        second = ((second & 0b11110000) >> 4) * 10 + (second & 0b00001111)

        self.date = f'{year + 2000}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}'

    def get_firmware_id(self):

        try:

            self.firmware_id = self.read_register(0x00)
            logger.info(f'firmware id: {self.firmware_id}')

        except BaseException as e:

            self.firmware_id = 0

    def get_input_voltage(self):

        try:

            self.input_voltage = self.read_register(0x01) + self.read_register(0x02) / 100
            self.input_voltage += DIODE_VOLTAGE_DROP_OUT
            logger.info(f'input voltage: {self.input_voltage}')

        except BaseException as e:

            self.input_voltage = 0.0

    def get_output_voltage(self):

        try:

            self.output_voltage = self.read_register(0x03) + self.read_register(0x04) / 100
            logger.info(f'output voltage: {self.output_voltage}')

        except BaseException as e:

            self.output_voltage = 0.0

    def get_output_current(self):

        try:

            self.output_current = self.read_register(0x05) + self.read_register(0x06) / 100
            logger.info(f'output current: {self.output_current}')

        except BaseException as e:

            self.output_current = 0.0

    def get_power_mode(self):

        try:

            self.power_mode = self.read_register(0x07)
            logger.info(f'power mode: {self.power_mode}')

        except BaseException as e:

            self.power_mode = 0

    def get_firmware_revision(self):

        try:

            self.firmware_revision = self.read_register(0x12)
            logger.info(f'firmware revision: {self.firmware_revision}')

        except BaseException as e:

            self.firmware_revision = 0

    def is_alarm_startup_triggered(self):

        return self.read_register(0x9)

    def is_alarm_shutdown_triggered(self):

        return self.read_register(0xA)

    def get_latest_action_reason_code(self):

        return self.read_register(0xB)

    def get_latest_action_reason(self):

        code = self.get_latest_action_reason_code()

        reasons  = ['N/A', 'ALARM1', 'ALARM2', 'button is clicked', 'input voltage too low', 'input voltage restored', 'over temperature', 'below temperature', 'ALARM1 delayed']

        if code >= 0 and code < len(reasons):

            return reasons[code]

        else:

            return f'unknown reason {code}'

    def get_startup_alarm(self):

        self.get_alarms()

        return self.startup_alarm

    def set_startup_alarm(self, day, hour, minute):

        success = False

        if day > 0 and day < 32 and hour >= 0 and hour <= 23 and minute >= 0 and minute < 60:

            day_bcd = ((day // 10) << 4)+ (day - 10 * (day // 10))
            hour_bcd = ((hour // 10) << 4) + (hour - 10 * (hour // 10))
            minute_bcd = ((minute // 10) << 4) + (minute - 10 * (minute // 10))

            success = self.write_register(0x1B, 0)

            success = self.write_register(0x1C, minute_bcd)

            success = self.write_register(0x1D, hour_bcd)

            success = self.write_register(0x1E, day_bcd)

            logger.info(f'startup alarm set to {day:02d} {hour:02d}:{minute:02d}')

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

            success = self.write_register(0x20, 0)

            success = self.write_register(0x21, minute_bcd)

            success = self.write_register(0x22, hour_bcd)

            success = self.write_register(0x23, day_bcd)

            logger.info(f'shutdown alarm set to {day:02d} {hour:02d}:{minute:02d}')

        return success

    def get_alarms(self):

        try:

            self.startup_alarm[0] = self.read_register(0x1B) # Seconds
            self.startup_alarm[1] = self.read_register(0x1C) # Minutes
            self.startup_alarm[2] = self.read_register(0x1D) # Hours
            self.startup_alarm[3] = self.read_register(0x1E) # Day
            self.startup_alarm[4] = self.read_register(0x1F) # Weekday

            self.shutdown_alarm[0] = self.read_register(0x20) # Seconds
            self.shutdown_alarm[1] = self.read_register(0x21) # Minutes
            self.shutdown_alarm[2] = self.read_register(0x22) # Hours
            self.shutdown_alarm[3] = self.read_register(0x23) # Day
            self.shutdown_alarm[4] = self.read_register(0x24) # Weekday

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

            success = self.write_register(0x2B, action)
            success = self.write_register(0x2C, threshold)

            logger.info(f'below temperature set to {threshold} and action set to {action}')

        return success

    def get_below_temperature(self):

        self.below_temperature_action = self.read_register(0x2B)
        self.below_temperature_threshold = self.read_register(0x2C)

    def set_over_temperature(self, action, threshold):

        success = False

        if threshold >= TEMPERATURE_MIN_THRESHOLD and threshold <= TEMPERATURE_MAX_THRESHOLD and action in [0, 1, 2]:

            success = self.write_register(0x2D, action)
            success = self.write_register(0x2E, threshold)

            logger.info(f'over temperature set to {threshold} and action set to {action}')

        return success

    def get_over_temperature(self):

        self.over_temperature_action = self.read_register(0x2D)
        self.over_temperature_threshold = self.read_register(0x2E)

    def set_led_pulse_interval(self, interval):

        try:

            interval = int(interval)

            if interval > 0 and interval < 255:

                success = self.write_register(0x12, interval)

                logger.info(f'led pulse interval set to {interval} seconds')

        except BaseException as e:

            logger.error(str(e))

    def get_led_pulse_interval(self):

        self.led_pulse_interval = self.read_register(0x12)

    def set_led_light_up_duration(self, duration):

        try:

            duration = int(duration)

            if duration > 0 and duration < 255:

                success = self.write_register(0x14, duration)

                logger.info(f'led light up duration set to {duration} milliseconds')

        except BaseException as e:

            logger.error(str(e))

    def get_led_light_up_duration(self):

        self.led_light_up_duration = self.read_register(0x14)

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
        s += f'  Below temperature action: {self.below_temperature_action}\n'
        s += f'  Below temperature threshold: {self.below_temperature_threshold}\n'
        s += f'  Over temperature action: {self.over_temperature_action}\n'
        s += f'  Over temperature threshold: {self.over_temperature_threshold}\n'
        s += f'  LED pulse interval: {self.led_pulse_interval}\n'
        s += f'  LED light up duration: {self.led_light_up_duration}\n'

        return s

def main():

    witty_pi = WittyPi()

    # witty_pi.set_startup_alarm(14, 16, 39)
    # witty_pi.set_shutdown_alarm(14, 16, 37)

    print(witty_pi)

    # for i in range(0,50):
        # witty_pi.get_output_current()
        # print(f'{witty_pi.output_current:.3f} ', end='')
        # sleep(0.1)

if __name__ == '__main__':

    main()

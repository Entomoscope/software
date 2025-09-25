import os
import time
import subprocess

from globals_parameters import SCHEDULE_FILE_PATH, SCHEDULE_SCRIPT_PATH

class Scheduler:

    def __init__(self):

        self.begin = ''
        self.end = ''
        self.on = ''
        self.off = ''

        self.file = SCHEDULE_FILE_PATH

        if os.path.exists(SCHEDULE_FILE_PATH):
            self.load()

    def load(self):

        if os.path.exists(self.file):

            with open(self.file, 'r') as f:
                lines = f.readlines()

            for line in lines:
                if line.startswith('BEGIN'):
                    self.begin = line.strip().split('#')[0]
                elif line.startswith('END'):
                    self.end = line.strip().split('#')[0]
                elif line.startswith('ON'):
                    self.on = line.strip().split('#')[0]
                elif line.startswith('OFF'):
                    self.off = line.strip().split('#')[0]

    def enable(self):

        if self.begin and self.end and self.on and self.off:
            self.save()

    def disable(self):

        if os.path.exists(SCHEDULE_FILE_PATH):
            os.remove(SCHEDULE_FILE_PATH)

    def save(self, header=None):

        with open(self.file, 'w') as f:
            if header:
                f.write(header)
                f.write('\n')
            f.write('{}\n'.format(self.begin))
            f.write('{}\n'.format(self.end))
            f.write('{}\n'.format(self.on))
            f.write('{}\n'.format(self.off))

    def set(self, wakeupHour, wakeupMinute, sleepHour, sleepMinute, onMinute=None, offMinute=None):

        # https://www.uugear.com/forums/technial-support-discussion/witty-pi-4-about-daylight-saving-time-dst/
        if time.localtime().tm_isdst:
            hourOffset = 1
        else:
            hourOffset = 0

        self.begin = f'BEGIN 2025-01-01 {wakeupHour-hourOffset:02d}:{wakeupMinute:02d}:00'
        self.end = 'END 2035-07-31 23:59:59'


# set_startup_time()
# {
  # sec=$(dec2bcd $4)
  # i2c_write 0x01 $I2C_MC_ADDRESS $I2C_CONF_SECOND_ALARM1 $sec
  # min=$(dec2bcd $3)
  # i2c_write 0x01 $I2C_MC_ADDRESS $I2C_CONF_MINUTE_ALARM1 $min
  # hour=$(dec2bcd $2)
  # i2c_write 0x01 $I2C_MC_ADDRESS $I2C_CONF_HOUR_ALARM1 $hour
  # date=$(dec2bcd $1)
  # i2c_write 0x01 $I2C_MC_ADDRESS $I2C_CONF_DAY_ALARM1 $date
# }

# dec2bcd()
# {
  # local result=$((10#$1/10*16+(10#$1%10)))
  # echo $result
# }
 

        if onMinute and offMinute:

            self.on = f'ON M{onMinute}'
            self.off = f'OFF M{offMinute}'

        else:

            sleepTimeInMinutes = sleepHour*60 + sleepMinute
            wakeupTimeInMinutes = wakeupHour*60 + wakeupMinute

            if sleepTimeInMinutes > wakeupTimeInMinutes:

                delta = sleepTimeInMinutes - wakeupTimeInMinutes
                hours = delta//60
                minutes = delta - hours*60
                if hours > 0:
                    self.on = f'ON H{hours} M{minutes}'
                else:
                    self.on = f'ON M{minutes}'
                delta = 24*60 - sleepTimeInMinutes + wakeupTimeInMinutes
                hours = delta//60
                minutes = delta - hours*60
                if hours > 0:
                    self.off = f'OFF H{hours} M{minutes}'
                else:
                    self.off = f'OFF M{minutes}'

            else:

                delta = 24*60 - wakeupTimeInMinutes + sleepTimeInMinutes
                hours = delta//60
                minutes = delta - hours*60
                if hours > 0:
                    self.on = f'ON H{hours} M{minutes}'
                else:
                    self.on = f'ON M{minutes}'
                delta = wakeupTimeInMinutes - sleepTimeInMinutes
                hours = delta//60
                minutes = delta - hours*60
                if hours > 0:
                    self.off = f'OFF H{hours} M{minutes}'
                else:
                    self.off = f'OFF M{minutes}'


    def runScript(self, wittypi_script_path=SCHEDULE_SCRIPT_PATH):

        output = subprocess.check_output(['sudo', wittypi_script_path])

        return output

    def __str__(self):

        s = 'BEGIN: ' + self.begin + '\n'
        s += 'END: ' + self.end + '\n'
        s += 'ON: ' + self.on + '\n'
        s += 'OFF: ' + self.off + '\n'

        return s

if __name__ == '__main__':

    scheduler = Scheduler()

    print(scheduler)

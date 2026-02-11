#! /usr/bin/python3

from subprocess import check_output, call

# sudo timedatectl set-ntp on
# sudo timedatectl set-ntp off

# date --set HH:MM:SS --utc

class DateTime():

    def __init__(self):

        self.get_date()
        self.get_time()
        self.get_date_time_info()

    def get_date_time_info(self):

        info = [x.strip() for x in check_output('timedatectl', shell=True).decode('utf-8').split('\n')]

        self.date_time_info = [info[0], info[3]]

    def get_date(self):

        self.date = check_output('date "+%Y-%m-%d"', shell=True).decode('utf-8').strip()

    def get_time(self):

        self.time = check_output('date "+%H:%M:%S"', shell=True).decode('utf-8').strip()

    def set_time_utc(self, year, month, day, hours, minutes, seconds):

        cmd = f'sudo date --set "{year}-{month:02d}-{day:02d} {hours:02d}:{minutes:02d}:{seconds:02d}" --utc'

        call(cmd, shell=True)

    def set_time(self, year, month, day, hours, minutes, seconds):

        cmd = f'sudo date --set "{year}-{month:02d}-{day:02d} {hours:02d}:{minutes:02d}:{seconds:02d}"'

        call(cmd, shell=True)

    def set_time(self, date, time):

        cmd = f'sudo date --set "{date} {time}"'

        call(cmd, shell=True)

    def start_web_synchronisation(self):

        cmd = 'sudo timedatectl set-ntp on'

        call(cmd, shell=True)

    def stop_web_synchronisation(self):

        cmd = 'sudo timedatectl set-ntp off'

        call(cmd, shell=True)

    def __str__(self):

        s = ''

        s += 'Date: ' + self.date + '\n'
        s += 'Time: ' + self.time + '\n'
        s += '\n'.join(self.date_time_info)

        return s

if __name__ == '__main__':

    datetime = DateTime()

    print(datetime)

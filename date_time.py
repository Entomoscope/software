#! /usr/bin/python3

from subprocess import check_output, call

# sudo timedatectl set-ntp on
# sudo timedatectl set-ntp off

# date --set HH:MM:SS --utc

class DateTime():

    def __init__(self):

        self.get_date_time_info()

    def get_date_time_info(self):

        info = [x.strip() for x in check_output('timedatectl').decode('utf-8').split('\n')]

        self.date_time_info = [info[0], info[3]]

    def set_time_utc(self, year, month, day, hours, minutes, seconds):

        cmd = f'sudo date --set "{year}-{month:02d}-{day:02d} {hours:02d}:{minutes:02d}:{seconds:02d}" --utc'

        call(cmd, shell=True)

    def __str__(self):

        return '\n'.join(self.date_time_info)

if __name__ == '__main__':

    datetime = DateTime()

    print(datetime)

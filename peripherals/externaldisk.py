import os
import sys
from subprocess import check_output, CalledProcessError

import logging
from logging.handlers import RotatingFileHandler

sys.path.append('..')

from globals_parameters import EXTERNAL_DISK_FOLDER, LOGS_DESKTOP_FOLDER, TODAY

# How to set up an SSD with the Raspberry Pi 4
# https://thepihut.com/blogs/raspberry-pi-tutorials/how-to-set-up-an-ssd-with-the-raspberry-pi

# for testing external hdd with smartctl
# https://gist.github.com/meinside/0538087cc60a2f0654bb
# sudo apt install smartmontools
# sudo smartctl -t short -d sat /dev/sda1
# sudo smartctl -t long -d sat /dev/sda1 -T permissive
# sudo smartctl -l selftest -d sat /dev/sda1 -T permissive

# Volume renaming
# sudo e2label /dev/sda1 ENTO_EXT_DISK

# blkid -L ENTO_EXT_DRIVE
# blkid -s UUID -o value /dev/sda1

# Mount / Unmount
# https://debian-facile.org/doc:systeme:udisks

# Ajout permission en écriture
# sudo chown $USER:$USER /media/entomoscope/ENTO_EXT_DISK

this_script = os.path.basename(__file__)[:-3]

today_log_path = os.path.join(LOGS_DESKTOP_FOLDER, TODAY)
if not os.path.exists(today_log_path):
    os.mkdir(today_log_path)

logger = logging.getLogger('entomoscope_externaldisk')
filename = os.path.join(today_log_path, TODAY + '_' + this_script + '.log')
file_handler = RotatingFileHandler(filename, mode="a", maxBytes=50000, backupCount=100, encoding="utf-8")
logger.addHandler(file_handler)
formatter = logging.Formatter('%(asctime)s;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
file_handler.setFormatter(formatter)
logger.setLevel("DEBUG")

class ExternalDisk():

    def __init__(self, volume_name='ENTO_EXT_DISK'):

        self.volume_name = volume_name
        self.path = ''
        self.mounted = False
        self.size = 0
        self.used = 0
        self.target = ''
        self.uuid = ''

        self.find_path()

        if self.path:
            self.available = True
            self.is_mounted()
            if self.mounted:
                self.get_info()
        else:
            self.available = False

    def find_path(self):

        try:
            self.path = check_output(['sudo', 'blkid', '-L', self.volume_name]).decode('utf-8').strip()
            logger.info(f'external disk found at {self.path}')
        except CalledProcessError as e:
            logger.error('external disk not found')
            logger.error(str(e))

    def mount(self):

        if self.available:

            if not self.mounted:

                try:
                    logger.info('mounting disk...')
                    check_output(['sudo', 'mount', '-t', 'ntfs-3g', self.path, EXTERNAL_DISK_FOLDER])
                    self.is_mounted()
                except CalledProcessError as e:
                    logger.error('mounting disk failed')
                    logger.error(str(e))

            else:

                logger.warning('disk already mounted')

    def unmount(self):

        if self.available:

            if self.mounted:

                try:
                    logger.info('unmounting disk...')
                    check_output(['sudo', 'umount', self.path])
                    self.is_mounted()
                except CalledProcessError as e:
                    logger.error('unmounting disk failed')
                    logger.error(str(e))

            else:

                logger.warning('disk already unmounted')


    def is_mounted(self):

        self.mounted = False

        if self.available:

            try:
                outputs = check_output(['cat', '/proc/mounts']).decode('utf-8').split('\n')
                for output in outputs:
                    if len(output) > 0 and output.split()[0].strip().startswith(self.path):
                        self.mounted = True
                        break
            except CalledProcessError as e:
                logger.error(str(e))

            logger.info(f'is disk mounted? {self.mounted}')

    def get_info(self):

        if self.available:

            try:
                outputs = check_output(['df', self.path, '--output=size,pcent,target']).decode('utf-8').split('\n')[1].split()
                self.size = int(outputs[0])
                self.used = int(outputs[1].replace('%', ''))
                self.target = outputs[2]
            except CalledProcessError as e:
                logger.error(str(e))

            try:
                self.uuid = check_output(['sudo', 'blkid', '-s', 'UUID', '-o', 'value', self.path]).decode('utf-8').strip()
            except CalledProcessError as e:
                logger.error(str(e))

            logger.info('external disk path: ' + self.path)
            logger.info('external disk UUID: ' + self.uuid)
            logger.info('external disk mounted: ' + ('True' if self.mounted else 'False'))
            logger.info(f'external disk size: {self.size}')
            logger.info(f'external disk used: {self.used}%')
            logger.info('external disk target: ' + self.target)

    def __str__(self):

        s = 'External Drive\n'
        s += '  Path: ' + self.path + '\n'
        s += '  UUID: ' + self.uuid + '\n'
        s += '  Mounted: ' + ('True' if self.mounted else 'False') + '\n'
        s += f'  Size: {self.size}\n'
        s += f'  Used: {self.used}%\n'
        s += '  Target: ' + self.target

        return s


if __name__ == '__main__':

    external_disk_already_mounted = False

    external_disk = ExternalDisk()

    if external_disk.available:

        if not external_disk.mounted:
            external_disk.mount()
            if external_disk.mounted:
                print('External disk mounted')
        else:
            external_disk_already_mounted = True
            print('External disk already mounted')

        if external_disk.mounted:
            external_disk.get_info()

        print(external_disk)

        if not external_disk_already_mounted and external_disk.mounted:
            external_disk.unmount()
            print('External disk unmounted')

    else:

        print('External disk not found')

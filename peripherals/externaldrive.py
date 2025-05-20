import os
from subprocess import check_output, CalledProcessError

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

class ExternalDrive():

    def __init__(self, volume_name='ENTO_EXT_DISK'):

        self.volume_name = volume_name
        self.path = ''
        self.mounted = False
        self.size = 0
        self.used = 0
        self.target = ''
        self.uuid = ''

        self.last_error = ''

        self.find_path()

        if self.path:
            self.is_mounted()
            if self.mounted:
                self.get_info()

    def find_path(self):

        try:
            self.path = check_output(['blkid', '-L', self.volume_name]).decode('utf-8').strip()
        except CalledProcessError as e:
            self.last_error = str(e)

    def mount(self):

        if not self.mounted and self.path:

            try:
                check_output(['udisksctl', 'mount', '-b', self.path])
                self.is_mounted()
            except CalledProcessError as e:
                self.last_error = str(e)

    def unmount(self):

        if self.mounted and self.path:

            try:
                check_output(['udisksctl', 'unmount', '-b', self.path])
                self.is_mounted()
            except CalledProcessError as e:
                self.last_error = str(e)

    def is_mounted(self):

        self.mounted = False

        if self.path:

            try:
                outputs = check_output(['cat', '/proc/mounts']).decode('utf-8').split('\n')
                for output in outputs:

                    if len(output) > 0 and output.split()[0].strip().startswith(self.path):
                        self.mounted = True
                        break
            except CalledProcessError as e:
                self.last_error = str(e)

    def get_info(self):

        if self.path:

            try:
                outputs = check_output(['df', self.path, '--output=size,pcent,target']).decode('utf-8').split('\n')[1].split()
                self.size = int(outputs[0])
                self.used = int(outputs[1].replace('%', ''))
                self.target = outputs[2]
                # print(uuid)
                # if uuid != b'':
                    # self.uuid = uuid
            except CalledProcessError as e:
                self.last_error = str(e)

            try:
                self.uuid = check_output(['blkid', '-s', 'UUID', '-o', 'value', self.path]).decode('utf-8').strip()
                # print(uuid)
                # if uuid != b'':
                    # self.uuid = uuid
            except CalledProcessError as e:
                self.last_error = str(e)

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

    drive_already_mounted = False

    ext_drive = ExternalDrive()

    if not ext_drive.mounted:
        ext_drive.mount()
        if ext_drive.mounted:
            print('Drive mounted')
    else:
        drive_already_mounted = True
        print('Drive already mounted')

    if ext_drive.mounted:
        ext_drive.get_info()

    print(ext_drive)

    if not drive_already_mounted and ext_drive.mounted:
        ext_drive.unmount()
        print('Drive unmounted')

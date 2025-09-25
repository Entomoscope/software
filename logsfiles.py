#! /usr/bin/python3

import os

from zipfile import ZipFile, ZIP_DEFLATED

from subprocess import run, CalledProcessError

from datetime import datetime

from globals_parameters import LOGS_DESKTOP_FOLDER, TODAY, WITTY_PI_FOLDER, USER_FOLDER

class LogsFiles():

    def __init__(self):

        pass

    def backup(self):

        self.list()

        try:

            with ZipFile(os.path.join(LOGS_DESKTOP_FOLDER, 'Logs_' + datetime.now().strftime('%Y%m%d%H%M%S') + '.zip'), 'w', ZIP_DEFLATED) as zipf:

                # Entomoscope logs
                for fp in self.files_path:
                    zipf.write(os.path.join(LOGS_DESKTOP_FOLDER, TODAY, fp))

                # Witty Pi logs
                zipf.write(os.path.join(WITTY_PI_FOLDER, 'wittyPi.log'))

                # journalctl
                try:

                    if os.path.exists(os.path.join(USER_FOLDER, 'journalctl.log')):
                        os.remove(os.path.join(USER_FOLDER, 'journalctl.log'))
                    with open(os.path.join(USER_FOLDER, 'journalctl.log'), "w") as outfile:
                        run(['journalctl'], stdout=outfile)
                    if os.path.exists(os.path.join(USER_FOLDER, 'journalctl.log')):
                        zipf.write(os.path.join(USER_FOLDER, 'journalctl.log'))
                        os.remove(os.path.join(USER_FOLDER, 'journalctl.log'))

                except CalledProcessError as e:

                    print(str(e))

                # journalctl err
                try:

                    if os.path.exists(os.path.join(USER_FOLDER, 'journalctl_err.log')):
                        os.remove(os.path.join(USER_FOLDER, 'journalctl_err.log'))
                    with open(os.path.join(USER_FOLDER, 'journalctl_err.log'), "w") as outfile:
                        run(['journalctl', '-p', 'err'], stdout=outfile)
                    if os.path.exists(os.path.join(USER_FOLDER, 'journalctl_err.log')):
                        zipf.write(os.path.join(USER_FOLDER, 'journalctl_err.log'))
                        os.remove(os.path.join(USER_FOLDER, 'journalctl_err.log'))

                except CalledProcessError as e:

                    print(str(e))

                # journalctl cron
                try:

                    if os.path.exists(os.path.join(USER_FOLDER, 'journalctl_cron.log')):
                        os.remove(os.path.join(USER_FOLDER, 'journalctl_cron.log'))
                    with open(os.path.join(USER_FOLDER, 'journalctl_cron.log'), "w") as outfile:
                        run(['journalctl', '-t', 'CRON'], stdout=outfile)
                    if os.path.exists(os.path.join(USER_FOLDER, 'journalctl_cron.log')):
                        zipf.write(os.path.join(USER_FOLDER, 'journalctl_cron.log'))
                        os.remove(os.path.join(USER_FOLDER, 'journalctl_cron.log'))

                except CalledProcessError as e:

                    print(str(e))

                # dmesg
                try:

                    if os.path.exists(os.path.join(USER_FOLDER, 'dmesg.log')):
                        os.remove(os.path.join(USER_FOLDER, 'dmesg.log'))
                    with open(os.path.join(USER_FOLDER, 'dmesg.log'), "w") as outfile:
                        run(['dmesg', '-HTx'], stdout=outfile)
                    if os.path.exists(os.path.join(USER_FOLDER, 'dmesg.log')):
                        zipf.write(os.path.join(USER_FOLDER, 'dmesg.log'))
                        os.remove(os.path.join(USER_FOLDER, 'dmesg.log'))

                except CalledProcessError as e:

                    print(str(e))

        except BaseException as e:

            print(str(e))

    def clear(self):

        self.backup()

        for fp in self.files_path:
            if os.path.exists(os.path.join(LOGS_DESKTOP_FOLDER, TODAY, fp)):
                open(os.path.join(LOGS_DESKTOP_FOLDER, TODAY, fp), 'w').close()

        if os.path.exists(os.path.join(WITTY_PI_FOLDER, 'wittyPi.log')):
            open(os.path.join(WITTY_PI_FOLDER, 'wittyPi.log'), 'w').close()

    def list(self):

        self.files_path = os.listdir(os.path.join(LOGS_DESKTOP_FOLDER, TODAY))

        # self.files = sorted([os.path.basename(x.replace(TODAY + '_', ''))[0:-4] for x in self.files_path])

        self.files = self.files = sorted([os.path.basename(x.replace(TODAY + '_', '')) for x in self.files_path])

        # self.names = [x.replace('_', ' ').replace('2', '').capitalize() for x in self.files]
        self.names = [x.capitalize() for x in self.files]

    def __str__(self):

        s = ''
        for f in self.files:

            s += f + '\n'

        return s

if __name__ == '__main__':

    logs_files = LogsFiles()

    logs_files.backup()

    logs_files.list()

    print(logs_files)

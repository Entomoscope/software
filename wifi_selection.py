#! /usr/bin/python3

import os
from subprocess import check_output, CalledProcessError
from time import time, sleep

import logging
from logging.handlers import RotatingFileHandler

import pigpio

from globals_parameters import LOGS_DESKTOP_FOLDER, TODAY, WIFI_CONNECTION_TRY_DURATION
from peripherals.pinout2 import TOGGLE_SWITCH_PIN_1, TOGGLE_SWITCH_PIN_2
from peripherals.wifi import Wifi
from configuration2 import Configuration2

this_script = os.path.basename(__file__)[:-3]

today_log_path = os.path.join(LOGS_DESKTOP_FOLDER, TODAY)
if not os.path.exists(today_log_path):
    os.mkdir(today_log_path)

logger = logging.getLogger('entomoscope' + '_' + this_script)
filename = os.path.join(today_log_path, TODAY + '_' + this_script + '.log')
file_handler = RotatingFileHandler(filename, mode="a", maxBytes=50000, backupCount=100, encoding="utf-8")
logger.addHandler(file_handler)
formatter = logging.Formatter('%(asctime)s.%(msecs)03d;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
file_handler.setFormatter(formatter)
logger.setLevel("DEBUG")

def get_nmcli_error(exception_string):

    num = exception_string.split(' ')[-1].split('.')[0]

    if num == '0':
        error_string = 'Success – indicates the operation succeeded.'
    elif num == '1':
        error_string = 'Unknown or unspecified error.'
    elif num == '2':
        error_string = 'Invalid user input, wrong nmcli invocation.'
    elif num == '3':
        error_string = f'Timeout expired ({WIFI_CONNECTION_TRY_DURATION} seconds).'
    elif num == '4':
        error_string = 'Connection activation failed.'
    elif num == '5':
        error_string = 'Connection deactivation failed.'
    elif num == '6':
        error_string = 'Disconnecting device failed.'
    elif num == '7':
        error_string = 'Connection deletion failed.'
    elif num == '8':
        error_string = 'NetworkManager is not running.'
    elif num == '10':
        error_string = 'Connection, device, or access point does not exist.'
    elif num == '65':
        error_string = 'When used with --complete-args option, a file name is expected to follow.'

    return error_string

def run():

    pi = pigpio.pi()

    wifi = Wifi()

    configuration = Configuration2()
    configuration.read()

    wifi_selected = [False, False]

    ssids = [wifi.ap_name, configuration.wifi['station_ssid']]

    wifi_idx = None

    activate_wifi = False
    desactivate_wifi = False

    s = time()
    # ss = time()

    print('start')

    while True:

        try:

            if time() - s > 1:

                s = time()

                tsp = [pi.read(TOGGLE_SWITCH_PIN_1), pi.read(TOGGLE_SWITCH_PIN_2)]

                if any(tsp):

                    # output = check_output('rfkill unblock wifi', shell=True).decode('utf-8').split('\n')

                    # print(output)

                    if tsp[0] and not wifi_selected[0]:

                        logger.info(f'Switch toggled: try to connect to {ssids[0]}')

                        try:

                            output = check_output(f'sudo nmcli c mod "{ssids[0]}" connection.autoconnect-retries 1 connection.autoconnect no', shell=True).decode('utf-8').split('\n')
                            for out in output:
                                if out:
                                    logger.info(out)
                            output = check_output(f'sudo nmcli -w {WIFI_CONNECTION_TRY_DURATION} c up "{ssids[0]}"', shell=True).decode('utf-8').split('\n')
                            for out in output:
                                if out:
                                    logger.info(out)

                            wifi_selected[0] = True
                            wifi_idx = 0

                            logger.info(f'Connected to {ssids[0]}')

                        except CalledProcessError as e:

                            error_string = get_nmcli_error(str(e))

                            logger.error(f'Unable to connected to {ssids[0]}')

                            logger.error(error_string)

                    if tsp[1] and not wifi_selected[1]:

                        logger.info(f'Switch toggled: try to connect to {ssids[1]}')

                        try:

                            output = check_output(f'sudo nmcli c mod "{ssids[1]}" connection.autoconnect-retries 1 connection.autoconnect no', shell=True).decode('utf-8').split('\n')
                            for out in output:
                                if out:
                                    logger.info(out)
                            output = check_output(f'sudo nmcli -w {WIFI_CONNECTION_TRY_DURATION} c up "{ssids[1]}"', shell=True).decode('utf-8').split('\n')
                            for out in output:
                                if out:
                                    logger.info(out)

                            wifi_selected[1] = True
                            wifi_idx = 1

                            logger.info(f'Connected to {ssids[1]}')

                        except CalledProcessError as e:

                            error_string = get_nmcli_error(str(e))

                            logger.error(f'Unable to connect to {ssids[1]}')

                            logger.error(error_string)

                else:

                    if any(wifi_selected):

                        try:

                            output = check_output(f'sudo nmcli c down "{ssids[wifi_idx]}"', shell=True).decode('utf-8').split('\n')
                            for out in output:
                                if out:
                                    logger.info(out)

                            # output = check_output('rfkill block wifi', shell=True).decode('utf-8').split('\n')

                            # print(output)

                            wifi_selected[wifi_idx] = False

                            logger.info(f'Disconnected from {ssids[wifi_idx]}')

                        except CalledProcessError as e:

                            error_string = get_nmcli_error(str(e))

                            logger.error(f'Unable to disconnect from {ssids[wifi_idx]}')

                            logger.error(error_string)

            # if time() - ss > 50000:
                # break

            sleep(0.5)

        except KeyboardInterrupt:

            logger.warning('While loop ended by user')
            break

    print('end')

if __name__ == '__main__':

    run()

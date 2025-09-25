#! /usr/bin/python3

import os
from subprocess import run
import logging

from globals_parameters import LOGS_DESKTOP_FOLDER, TODAY

this_script = os.path.basename(__file__)[:-3]

today_log_path = os.path.join(LOGS_DESKTOP_FOLDER, TODAY)
if not os.path.exists(today_log_path):
    os.mkdir(today_log_path)

logger = logging.getLogger('entomoscope_updates')
filename = os.path.join(today_log_path, TODAY + '_' + this_script + '.log')
file_handler = logging.FileHandler(filename, mode="a", encoding="utf-8")
logger.addHandler(file_handler)
formatter = logging.Formatter('%(asctime)s;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
file_handler.setFormatter(formatter)
logger.setLevel("DEBUG")

updates_available = False

def updates_check():

    global updates_available

    # Check for update on the GitHub repo
    logger.info('updates checking...')

    try:

        logger.info('fetching...')
        result = run(['git', 'fetch'], timeout=10, text=True, capture_output=True)

        if result.returncode == 0:

            logger.info('status...')
            result = run(['git', 'status'], timeout=10, text=True, capture_output=True)

            if result.returncode == 0:

                if 'Your branch is behind' in result.stdout:
                    logger.info('updates available')
                    updates_available = True
                else:
                    logger.info('no updates available')
                    updates_available = False

            else:
                logger.error(result.stderr.strip())
                updates_available = False
        else:

            logger.error(result.stderr.strip())
            updates_available = False

    except Exception as e:

        logger.error(str(e))
        updates_available = False

    return updates_available

def updates_get():

    if updates_available:

        try:

            logger.info('pulling updates...')
            result = run(['git', 'pull'], text=True, capture_output=True)

            if result.returncode == 0:
                logger.info(result.stdout.strip())
                updates_done = True
            else:
                logger.error(result.stderr.strip())
                updates_done = False

        except Exception as e:

            logger.error(str(e))
            updates_done = False

    else:

        logger.info('no updates available => nothing to update')
        updates_done = False

    return updates_done

if __name__ == '__main__':

    updates_available = updates_check()

    if updates_available:
        print('Updates available => get updates')
        updates_get()
    else:
        print('No updates available')

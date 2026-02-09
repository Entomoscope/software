#! /usr/bin/python3

import os
from subprocess import run
import logging

from globals_parameters import PYTHON_SCRIPTS_BASE_FOLDER, LOGS_DESKTOP_FOLDER, TODAY

# Cloning the repo :
# git clone https://github.com/Entomoscope/software.git /home/entomoscope/Entomoscope

this_script = os.path.basename(__file__)[:-3]

today_log_path = os.path.join(LOGS_DESKTOP_FOLDER, TODAY)
if not os.path.exists(today_log_path):
    os.mkdir(today_log_path)

logger = logging.getLogger('entomoscope_updates')
filename = os.path.join(today_log_path, TODAY + '_' + this_script + '.log')
file_handler = logging.FileHandler(filename, mode="a", encoding="utf-8")
logger.addHandler(file_handler)
formatter = logging.Formatter('%(asctime)s.%(msecs)03d;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
file_handler.setFormatter(formatter)
logger.setLevel("DEBUG")

updates_available = False

git_folder = os.path.join(PYTHON_SCRIPTS_BASE_FOLDER)

def updates_check():

    global updates_available

    # Check for update on the GitHub repo
    logger.info('checking updates...')

    try:

        logger.info('fetching main branch...')
        result = run(['git', '-C', git_folder, 'fetch'], timeout=10, text=True, capture_output=True)

        if result.returncode == 0:

            logger.info('getting status...')
            result = run(['git', '-C', git_folder, 'status'], timeout=10, text=True, capture_output=True)

            if result.returncode == 0:

                for r in result.stdout.split('\n'):
                    logger.info(r)

                if 'Your branch is behind' in result.stdout:
                    updates_available = True
                else:
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
            result = run(['git', '-C', git_folder, 'pull'], text=True, capture_output=True)

            if result.returncode == 0:
                for r in result.stdout.split('\n'):
                    logger.info(r)
                updates_done = True
            else:
                for r in result.stderr.split('\n'):
                    logger.error(r)
                updates_done = False

        except Exception as e:

            logger.error(str(e))
            updates_done = False

    else:

        logger.info('no updates available => nothing to update')
        updates_done = False

    return updates_done

def updates_back_to_previous():

    try:

        logger.info('back to previous version...')
        result = run(['git', '-C', git_folder, 'reset', '--hard'], text=True, capture_output=True)

        if result.returncode == 0:
            for r in result.stdout.split('\n'):
                logger.info(r)
        else:
            for r in result.stderr.split('\n'):
                logger.error(r)

    except Exception as e:

        logger.error(str(e))

if __name__ == '__main__':

    updates_available = updates_check()

    if updates_available:
        print('Updates available => get updates')
        updates_get()
    else:
        print('No updates available')

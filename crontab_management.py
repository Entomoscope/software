#! /usr/bin/python3

import os
import logging
from logging.handlers import RotatingFileHandler

from crontab import CronTab

from globals_parameters import USER, LOGS_DESKTOP_FOLDER, TODAY
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

class CrontabManagement():


    def __init__(self, check_mandatory_service=False):

        self.cron = CronTab(user=USER)

        if check_mandatory_service:
            self.check_mandatory_service()


    def enable_service(self, service, data):

        cron_modified = False

        if service == 'fan_management':
            for job in self.cron:
                if job.comment.startswith('Entomoscope - Manage fan'):
                    job.enable()
                    job.minute.every(data)
                    job.comment = f'Entomoscope - Manage fan every {data} minutes'
                    cron_modified = True
                    logger.info('Manage fan service enabled')
        elif service == 'environmental_monitoring':
            for job in self.cron:
                if job.comment.startswith('Entomoscope - Monitor environment'):
                    job.enable()
                    job.minute.every(data)
                    job.comment = f'Entomoscope - Monitor environment every {data} minutes'
                    cron_modified = True
                    logger.info('Monitor environment service enabled')

        if cron_modified:
            self.cron.write()
            logger.info('Cron written')


    def disable_service(self, service):

        cron_modified = False

        if service == 'fan_management':
            for job in self.cron:
                if job.comment.startswith('Entomoscope - Manage fan'):
                    job.comment = f'Entomoscope - Manage fan disabled'
                    job.enable(False)
                    cron_modified = True
                    logger.info('Manage fan service disabled')
        elif service == 'environmental_monitoring':
            for job in self.cron:
                if job.comment.startswith('Entomoscope - Monitor environment'):
                    job.comment = f'Entomoscope - Monitor environment disabled'
                    job.enable(False)
                    cron_modified = True
                    logger.info('Monitor environment service disabled')

        if cron_modified:
            self.cron.write()
            logger.info('Cron written')


    def check_mandatory_service(self):

        try:

            cron_modified = False

            logger.info(f'Mandatory services check')

            configuration = Configuration2()
            configuration.read()

            startup_service_found = False
            images_capture_service_found = False
            sounds_capture_service_found = False
            flask_server_service_found = False
            monitor_environment_service_found = False
            manage_fan_service_found = False
            # wifi_selection_service_found = False
            wifi_disable_power_safe_service_found = False
            disable_daily_auto_update_service_found = False
            disable_daily_auto_update_timer_service_found = False
            disable_daily_auto_upgrade_service_found = False
            disable_daily_auto_upgrade_timer_service_found = False

            for job in self.cron:
                if job.comment.startswith('Entomoscope - Run startup'):
                    startup_service_found = True
                elif job.comment.startswith('Entomoscope - Run images capture'):
                    images_capture_service_found = True
                elif job.comment.startswith('Entomoscope - Run sounds capture'):
                    sounds_capture_service_found = True
                elif job.comment.startswith('Entomoscope - Run Flask server'):
                    flask_server_service_found = True
                # elif job.comment.startswith('Entomoscope - Run wifi selection'):
                    # wifi_selection_service_found = True
                elif job.comment.startswith('Entomoscope - Monitor environment'):
                    monitor_environment_service_found = True
                elif job.comment.startswith('Entomoscope - Manage fan'):
                    manage_fan_service_found = True
                elif job.comment.startswith('Entomoscope - Disable WiFi power management'):
                    wifi_disable_power_safe_service_found = True
                elif job.comment.startswith('Entomoscope - Disable daily auto update service'):
                    disable_daily_auto_update_service_found = True
                elif job.comment.startswith('Entomoscope - Disable daily auto update timer'):
                    disable_daily_auto_update_timer_service_found = True
                elif job.comment.startswith('Entomoscope - Disable daily auto upgrade service'):
                    disable_daily_auto_upgrade_service_found = True
                elif job.comment.startswith('Entomoscope - Disable daily auto upgrade timer'):
                    disable_daily_auto_upgrade_timer_service_found = True

            if not startup_service_found:
                logger.info('Startup service not found')
                job = self.cron.new(command='/usr/bin/python /home/entomoscope/Entomoscope/startup2.py', comment='Entomoscope - Run startup script at startup')
                job.every_reboot()
                cron_modified = True
                logger.info('Startup service created')
            if not images_capture_service_found:
                logger.info('Images capture service not found')
                job = self.cron.new(command='/usr/bin/python /home/entomoscope/Entomoscope/images_capture2.py', comment='Entomoscope - Run images capture script at startup')
                job.every_reboot()
                cron_modified = True
                logger.info('Images capture service created')
            if not sounds_capture_service_found:
                logger.info('Sounds capture service not found')
                job = self.cron.new(command='/usr/bin/python /home/entomoscope/Entomoscope/sounds_capture2.py', comment='Entomoscope - Run sounds capture script at startup')
                job.every_reboot()
                cron_modified = True
                logger.info('Sounds capture service created')
            if not flask_server_service_found:
                logger.info('Flask service not found')
                job = self.cron.new(command='/usr/bin/python /home/entomoscope/Entomoscope/server.py', comment='Entomoscope - Run Flask server at startup')
                job.every_reboot()
                cron_modified = True
                logger.info('Flask service created')
            # if not wifi_selection_service_found:
                # logger.info('Wifi selection service not found')
                # job = self.cron.new(command='/usr/bin/python /home/entomoscope/Entomoscope/wifi_selection.py', comment='Entomoscope - Run wifi selection script at startup')
                # job.every_reboot()
                # cron_modified = True
                # logger.info('Wifi selection service created')
            if not monitor_environment_service_found:
                logger.info('Monitor environment service not found')
                job = self.cron.new(command='/usr/bin/python /home/entomoscope/Entomoscope/environmental_monitoring.py', comment=f"Entomoscope - Monitor environment every {configuration.environmental_monitoring['time_step']} minutes")
                job.minutes.every(int(configuration.environmental_monitoring['time_step']))
                cron_modified = True
                logger.info('Monitor environment service created')
            if not manage_fan_service_found:
                logger.info('Manage fan service not found')
                job = self.cron.new(command='/usr/bin/python /home/entomoscope/Entomoscope/fan_management.py', comment=f"Entomoscope - Manage fan every {configuration.cooling_system['cpu_temperature_check_interval']} minutes")
                job.minutes.every(int(configuration.cooling_system['cpu_temperature_check_interval']))
                cron_modified = True
                logger.info('Manage fan service created')
            if not wifi_disable_power_safe_service_found:
                logger.info('Disable wifi power safe service not found')
                job = self.cron.new(command='sudo /usr/sbin/iw wlan0 set power_save off >> /home/entomoscope/Desktop/Logs/crontab_wifi_pwr_sav.log 2>&1 | logger t entomo_wifi_pwr_sav', comment='Entomoscope - Disable WiFi power management')
                job.every_reboot()
                cron_modified = True
                logger.info('Disable wifi power safe service created')
            if not disable_daily_auto_update_service_found:
                logger.info('Disable daily auto update service not found')
                job = self.cron.new(command='sudo systemctl disable apt-daily.service', comment='Entomoscope - Disable daily auto update service')
                job.every_reboot()
                cron_modified = True
                logger.info('Disable daily auto update service created')
            if not disable_daily_auto_update_timer_service_found:
                logger.info('Disable daily auto update timer not found')
                job = self.cron.new(command='sudo systemctl disable apt-daily.timer', comment='Entomoscope - Disable daily auto update timer')
                job.every_reboot()
                cron_modified = True
                logger.info('Disable daily auto update timer created')
            if not disable_daily_auto_upgrade_service_found:
                logger.info('Disable daily auto upgrade service not found')
                job = self.cron.new(command='sudo systemctl disable apt-daily-upgrade.service', comment='Entomoscope - Disable daily auto upgrade service')
                job.every_reboot()
                cron_modified = True
                logger.info('Disable daily auto upgrade service created')
            if not disable_daily_auto_upgrade_timer_service_found:
                logger.info('Disable daily auto upgrade timer not found')
                job = self.cron.new(command='sudo systemctl disable apt-daily-upgrade.timer', comment='Entomoscope - Disable daily auto upgrade timer')
                job.every_reboot()
                cron_modified = True
                logger.info('Disable daily auto upgrade timer created')

            if cron_modified:
                self.cron.write()
                logger.info('Cron written')

        except BaseException as e:

            logger.error(str(e))


if __name__ == '__main__':

    crontab = CrontabManagement(check_mandatory_service=False)

    # crontab.enable_service('fan_management', 5)

# @reboot /usr/bin/python /home/entomoscope/Entomoscope/startup2.py # Entomoscope - Run startup script at startup
# @reboot /usr/bin/python /home/entomoscope/Entomoscope/images_capture2.py # Entomoscope - Run images capture script at startup
# @reboot /usr/bin/python /home/entomoscope/Entomoscope/sounds_capture2.py # Entomoscope - Run sounds capture script at startup
# @reboot /usr/bin/python /home/entomoscope/Entomoscope/server.py # Entomoscope - Run Flask server at startup
# */5 * * * * /usr/bin/python /home/entomoscope/Entomoscope/environmental_monitoring.py # Entomoscope - Monitor environment every 5 minutes
# */5 * * * * /usr/bin/python /home/entomoscope/Entomoscope/fan_management.py # Entomoscope - Manage fan every 5 minutes

# @reboot /usr/bin/python /home/entomoscope/Entomoscope/wifi_selection.py # Entomoscope - Run wifi selection script at startup

# @reboot sudo /usr/sbin/iw wlan0 set power_save off >> /home/entomoscope/Desktop/Logs/crontab_wifi_pwr_sav.log 2>&1 | logger t entomo_wifi_pwr_sav # Entomoscope - Disable WiFi power management
# @reboot sudo systemctl disable apt-daily.service # Entomoscope - Disable daily auto update service
# @reboot sudo systemctl disable apt-daily.timer # Entomoscope - Disable daily auto update timer
# @reboot sudo systemctl disable apt-daily-upgrade.service # Entomoscope - Disable daily auto upgrade service
# @reboot sudo systemctl disable apt-daily-upgrade.timer # Entomoscope - Disable daily auto upgrade timer

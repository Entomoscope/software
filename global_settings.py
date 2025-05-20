#! /usr/bin/python3

import tkinter as tk
from tkinter import scrolledtext
from tkinter.ttk import Combobox
from tkinter.messagebox import askyesno
from tkinter.font import Font

import subprocess
import os

from time import sleep, time
import logging

from datetime import datetime

from functools import partial

import pigpio

pi = pigpio.pi()

from configuration import Configuration

from peripherals.pinout import IMAGES_CAPTURE_ACTIVITY_PIN, SOUNDS_CAPTURE_ACTIVITY_PIN, SHUTDOWN_PIN
from peripherals.rpi import Rpi
from peripherals.externaldrive import ExternalDrive

from scheduler import Scheduler
from globals_parameters import LOGS_FOLDER, TODAY, DELAY_BEFORE_SHUTDOWN, SAVE_FOLDER

VERSION = '1.0.0'

TK_WINDOWS_TITLE = 'Entomoscope - Global Settings - v' + VERSION

TK_WINDOW_WIDTH_IN_PX = 850
TK_WINDOW_HEIGHT_IN_PX = 800

TK_ENTRY_WIDTH = 5
TK_COMBOBOX_WIDTH = 5

EXT_DISK_INTERVAL = 60

CPU_TEMP_INTERVAL = 5

REFRESH_UI_INTERVAL_IN_MS = 1000

this_script = os.path.basename(__file__)[:-3]

logger = logging.getLogger('main')
filename = os.path.join(LOGS_FOLDER, TODAY + '_' + this_script + '.log')
logging.basicConfig(filename=filename,
                    format='%(asctime)s;%(levelname)s;"%(message)s"',
                    encoding='utf-8',
                    datefmt='%d/%m/%Y;%H:%M:%S',
                    level=logging.DEBUG)

class TkInterface(tk.Tk):

    def __init__(self):

        tk.Tk.__init__(self)

        self.title(TK_WINDOWS_TITLE)
        self.geometry(f'{TK_WINDOW_WIDTH_IN_PX}x{TK_WINDOW_HEIGHT_IN_PX}')

        self.font = Font(font='Consolas')
        self.font.config(size=8)

        self.protocol("WM_DELETE_WINDOW", self.close_window)

        self.last_time_cpu_temp = time()
        self.last_time_ext_disk = time()

        self.rpi = Rpi()
        self.configuration = Configuration()

        self.scheduler = Scheduler()

        self.external_drive = ExternalDrive()

        self.create_widgets()

        self.status_text.set('Ready')

    def close_window(self):

        logger.info(f'{this_script}: stop')

        self.quit()

    def create_widgets(self):

        self.option_add('*TCombobox*Listbox.font', self.font)

        # Bottom frame
        bottom_frame = tk.Frame(self)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, expand=False)

        self.status_text = tk.StringVar()
        self.status_text.set('Initializing...')
        self.status_label = tk.Label(bottom_frame, textvariable=self.status_text, font=self.font, bg='white')
        self.status_label.pack(fill=tk.BOTH, expand=True, pady=(5,0))

        left_frame = tk.Frame(self)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        right_frame = tk.Frame(self)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Images capture
        images_capture_label_frame = tk.LabelFrame(left_frame, text='Images Capture', font=self.font)
        images_capture_label_frame.pack(side=tk.TOP, fill=tk.X, padx=(5,5), pady=(0,5))

        images_capture_subframe_1 = tk.Frame(images_capture_label_frame)
        images_capture_subframe_1.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        images_capture_subframe_2 = tk.Frame(images_capture_label_frame)
        images_capture_subframe_2.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        images_capture_subframe_3 = tk.Frame(images_capture_label_frame)
        images_capture_subframe_3.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        images_capture_subframe_4 = tk.Frame(images_capture_label_frame)
        images_capture_subframe_4.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        images_capture_subframe_5 = tk.Frame(images_capture_label_frame)
        images_capture_subframe_5.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        images_capture_enable_label = tk.Label(images_capture_subframe_1, text='Enable', font=self.font)
        images_capture_enable_label.pack(side=tk.LEFT, padx=(5,5), pady=(0,5))

        self.images_capture_enable_combobox = Combobox(images_capture_subframe_1, values=['False', 'True'], state="readonly", width=TK_COMBOBOX_WIDTH, font=self.font)
        self.images_capture_enable_combobox.pack(side=tk.LEFT, padx=(0,5), pady=(0,5))
        if self.configuration.images_capture['enable']:
            self.images_capture_enable_combobox.current(1)
        else:
            self.images_capture_enable_combobox.current(0)

        self.images_capture_enable_set_button = tk.Button(images_capture_subframe_1, text='Save', command=self.save_images_capture_enable, font=self.font)
        self.images_capture_enable_set_button.pack(side=tk.RIGHT, padx=(0,5), pady=(0,5))

        self.images_capture_suspend_button_str = tk.StringVar()
        self.images_capture_running_label_str = tk.StringVar()

        if pi.read(SHUTDOWN_PIN) == 1:
                self.images_capture_suspend_button_str.set('Resume')
                self.images_capture_running_label_str.set('Stopped (reboot the system to restart)')
                bg = 'red'
        else:
            if pi.read(IMAGES_CAPTURE_ACTIVITY_PIN) == 1:
                self.images_capture_suspend_button_str.set('Resume')
                self.images_capture_running_label_str.set('Suspended (click on Resume to restart)')
                bg = 'orange'
            else:
                self.images_capture_suspend_button_str.set('Suspend')
                self.images_capture_running_label_str.set('Running (click on Suspend to pause)')
                bg = 'green'

        self.images_capture_running_canvas = tk.Canvas(images_capture_subframe_2, width=15, height=15)
        self.images_capture_running_canvas.pack(side=tk.LEFT, padx=(5,5))
        self.images_capture_running_state = self.images_capture_running_canvas.create_oval(1, 1, 15, 15, fill=bg, outline=bg)

        self.images_capture_running_label = tk.Label(images_capture_subframe_2, textvariable=self.images_capture_running_label_str, font=self.font)
        self.images_capture_running_label.pack(side=tk.LEFT, padx=(5,5))

        self.images_capture_stop_button = tk.Button(images_capture_subframe_2, text='Stop', command=self.stop_captures, font=self.font)
        self.images_capture_stop_button.pack(side=tk.RIGHT, padx=(0,5), pady=(0,5))

        self.images_capture_suspend_button = tk.Button(images_capture_subframe_2, textvariable=self.images_capture_suspend_button_str, command=self.manage_images_capture, font=self.font)
        self.images_capture_suspend_button.pack(side=tk.RIGHT, padx=(0,5), pady=(0,5))

        self.images_capture_time_step_label = tk.Label(images_capture_subframe_4, text='Time step between images (s)', font=self.font)
        self.images_capture_time_step_label.pack(side=tk.LEFT, padx=(5,5))

        self.images_capture_time_step_entry = tk.Entry(images_capture_subframe_4, width=TK_ENTRY_WIDTH, font=self.font)
        self.images_capture_time_step_entry.insert(0, str(self.configuration.images_capture['time_step']))
        self.images_capture_time_step_entry.pack(side=tk.LEFT, padx=(5,5))

        self.images_capture_time_step_set_button = tk.Button(images_capture_subframe_4, text='Save', command=self.save_images_capture_time_step, font=self.font)
        self.images_capture_time_step_set_button.pack(side=tk.RIGHT, padx=(0,5), pady=(0,5))

        if pi.read(SHUTDOWN_PIN) == 1:
            self.images_capture_stop_button.configure(state=tk.DISABLED)
            self.images_capture_suspend_button.configure(state=tk.DISABLED)
        else:
            if pi.read(IMAGES_CAPTURE_ACTIVITY_PIN) == 0:
                self.images_capture_time_step_entry.configure(state=tk.DISABLED)
                self.images_capture_time_step_set_button.configure(state=tk.DISABLED)

        # Laser
        laser_label_frame = tk.LabelFrame(left_frame, text='Laser', font=self.font)
        # laser_label_frame.pack(side=tk.TOP, fill=tk.X, padx=(5,5), pady=(0,5))

        laser_subframe = tk.Frame(laser_label_frame)
        laser_subframe.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        laser_enable_label = tk.Label(laser_subframe, text='Enable', font=self.font)
        laser_enable_label.pack(side=tk.LEFT, padx=(5,5), pady=(0,5))

        self.laser_enable_combobox = Combobox(laser_subframe, values=['False', 'True'], state="readonly", width=TK_COMBOBOX_WIDTH, font=self.font)
        self.laser_enable_combobox.pack(side=tk.LEFT, padx=(0,5), pady=(0,5))
        if self.configuration.laser['enable']:
            self.laser_enable_combobox.current(1)
        else:
            self.laser_enable_combobox.current(0)

        self.laser_enable_set_button = tk.Button(laser_subframe, text='Save', command=self.save_laser_enable, font=self.font)
        self.laser_enable_set_button.pack(side=tk.RIGHT, padx=(0,5), pady=(0,5))

        # Schedule
        schedule_label_frame = tk.LabelFrame(left_frame, text='Schedule', font=self.font)
        schedule_label_frame.pack(side=tk.TOP, fill=tk.X, padx=(5,5), pady=(0,5))

        schedule_subframe_1 = tk.Frame(schedule_label_frame)
        schedule_subframe_1.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        schedule_subframe_2 = tk.Frame(schedule_label_frame)
        schedule_subframe_2.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        schedule_subframe_3 = tk.Frame(schedule_label_frame)
        schedule_subframe_3.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        schedule_subframe_4 = tk.Frame(schedule_label_frame)
        schedule_subframe_4.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        schedule_subframe_5 = tk.Frame(schedule_label_frame)
        schedule_subframe_5.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        schedule_enable_label = tk.Label(schedule_subframe_1, text='Enable', font=self.font)
        schedule_enable_label.pack(side=tk.LEFT, padx=(5,5), pady=(0,5))

        self.schedule_enable_combobox = Combobox(schedule_subframe_1, values=['False', 'True'], state="readonly", width=TK_COMBOBOX_WIDTH, font=self.font)
        self.schedule_enable_combobox.pack(side=tk.LEFT, padx=(0,5), pady=(0,5))

        if self.configuration.schedule['enable']:
            self.schedule_enable_combobox.current(1)
        else:
            self.schedule_enable_combobox.current(0)

        self.schedule_enable_set_button = tk.Button(schedule_subframe_1, text='Save', command=self.save_schedule_enable, font=self.font)
        self.schedule_enable_set_button.pack(side=tk.RIGHT, padx=(0,5), pady=(0,5))

        wakeup_time = self.configuration.schedule['wakeup'].split(':')

        self.schedule_wakeup_hour_label = tk.Label(schedule_subframe_2, text='Wakeup (UTC)', font=self.font)
        self.schedule_wakeup_hour_label.pack(side=tk.LEFT, padx=(5,5))

        self.schedule_wakeup_hours_combobox = Combobox(schedule_subframe_2, values=[f'{x:02d}' for x in range(0,24)], state="readonly", width=TK_COMBOBOX_WIDTH, font=self.font)
        self.schedule_wakeup_hours_combobox.pack(side=tk.LEFT, padx=(0,5), pady=(0,5))
        self.schedule_wakeup_hours_combobox.current(int(wakeup_time[0]))

        schedule_colon_label = tk.Label(schedule_subframe_2, text=':', font=self.font)
        schedule_colon_label.pack(side=tk.LEFT, padx=(5,5))

        self.schedule_wakeup_minutes_combobox = Combobox(schedule_subframe_2, values=[f'{x:02d}' for x in range(0,60,5)], state="readonly", width=TK_COMBOBOX_WIDTH, font=self.font)
        self.schedule_wakeup_minutes_combobox.pack(side=tk.LEFT, padx=(0,5), pady=(0,5))
        self.schedule_wakeup_minutes_combobox.current(int(wakeup_time[1])//5)

        self.schedule_wakeup_set_button = tk.Button(schedule_subframe_2, text='Save', command=self.save_schedule_time, font=self.font)
        self.schedule_wakeup_set_button.pack(side=tk.RIGHT, padx=(0,5), pady=(0,5))

        sleep_time = self.configuration.schedule['sleep'].split(':')

        self.schedule_sleep_hour_label = tk.Label(schedule_subframe_3, text='Sleep (UTC)', font=self.font)
        self.schedule_sleep_hour_label.pack(side=tk.LEFT, padx=(5,5))

        self.schedule_sleep_hours_combobox = Combobox(schedule_subframe_3, values=[f'{x:02d}' for x in range(0,24)], state="readonly", width=TK_COMBOBOX_WIDTH, font=self.font)
        self.schedule_sleep_hours_combobox.pack(side=tk.LEFT, padx=(0,5), pady=(0,5))
        self.schedule_sleep_hours_combobox.current(int(sleep_time[0]))

        schedule_colon_label = tk.Label(schedule_subframe_3, text=':', font=self.font)
        schedule_colon_label.pack(side=tk.LEFT, padx=(5,5))

        self.schedule_sleep_minutes_combobox = Combobox(schedule_subframe_3, values=[f'{x:02d}' for x in range(0,60,5)], state="readonly", width=TK_COMBOBOX_WIDTH, font=self.font)
        self.schedule_sleep_minutes_combobox.pack(side=tk.LEFT, padx=(0,5), pady=(0,5))
        self.schedule_sleep_minutes_combobox.current(int(sleep_time[1])//5)

        self.schedule_sleep_set_button = tk.Button(schedule_subframe_3, text='Save', command=self.save_schedule_time, font=self.font)
        self.schedule_sleep_set_button.pack(side=tk.RIGHT, padx=(0,5), pady=(0,5))

        self.schedule_on_duration_label = tk.Label(schedule_subframe_4, text='On duration (min)', font=self.font)
        self.schedule_on_duration_label.pack(side=tk.LEFT, padx=(5,5))

        self.schedule_on_duration_entry = tk.Entry(schedule_subframe_4, width=TK_ENTRY_WIDTH, font=self.font)
        self.schedule_on_duration_entry.insert(0, str(self.configuration.schedule['on_duration']))
        self.schedule_on_duration_entry.pack(side=tk.LEFT, padx=(5,5))

        self.schedule_on_duration_set_button = tk.Button(schedule_subframe_4, text='Save', command=self.save_schedule_on_off, font=self.font)
        self.schedule_on_duration_set_button.pack(side=tk.RIGHT, padx=(0,5), pady=(0,5))

        self.schedule_off_duration_label = tk.Label(schedule_subframe_5, text='Off duration (min)', font=self.font)
        self.schedule_off_duration_label.pack(side=tk.LEFT, padx=(5,5))

        self.schedule_off_duration_entry = tk.Entry(schedule_subframe_5, width=TK_ENTRY_WIDTH, font=self.font)
        self.schedule_off_duration_entry.insert(0, str(self.configuration.schedule['off_duration']))
        self.schedule_off_duration_entry.pack(side=tk.LEFT, padx=(5,5))

        self.schedule_off_duration_set_button = tk.Button(schedule_subframe_5, text='Save', command=self.save_schedule_on_off, font=self.font)
        self.schedule_off_duration_set_button.pack(side=tk.RIGHT, padx=(0,5), pady=(0,5))

        # Site
        site_label_frame = tk.LabelFrame(left_frame, text='Site', font=self.font)
        site_label_frame.pack(side=tk.TOP, fill=tk.X, padx=(5,5), pady=(0,5))

        site_id_label = tk.Label(site_label_frame, text='ID', font=self.font)
        site_id_label.pack(side=tk.LEFT, padx=(5,5))

        self.site_id_entry = tk.Entry(site_label_frame, width=4*TK_ENTRY_WIDTH, font=self.font)
        self.site_id_entry.insert(0, str(self.configuration.site['id']))
        self.site_id_entry.pack(side=tk.LEFT, padx=(5,5))

        self.site_id_set_button = tk.Button(site_label_frame, text='Save', command=self.save_site_id, font=self.font)
        self.site_id_set_button.pack(side=tk.RIGHT, padx=(0,5), pady=(0,5))

        # Sounds capture
        sounds_capture_label_frame = tk.LabelFrame(left_frame, text='Sounds Capture', font=self.font)
        sounds_capture_label_frame.pack(side=tk.TOP, fill=tk.X, padx=(5,5), pady=(0,5))

        sounds_capture_subframe_1 = tk.Frame(sounds_capture_label_frame)
        sounds_capture_subframe_1.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        sounds_capture_subframe_2 = tk.Frame(sounds_capture_label_frame)
        sounds_capture_subframe_2.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        sounds_capture_subframe_3 = tk.Frame(sounds_capture_label_frame)
        sounds_capture_subframe_3.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        sounds_capture_enable_label = tk.Label(sounds_capture_subframe_1, text='Enable', font=self.font)
        sounds_capture_enable_label.pack(side=tk.LEFT, padx=(5,5), pady=(0,5))

        self.sounds_capture_enable_combobox = Combobox(sounds_capture_subframe_1, values=['False', 'True'], state="readonly", width=TK_COMBOBOX_WIDTH, font=self.font)
        self.sounds_capture_enable_combobox.pack(side=tk.LEFT, padx=(0,5), pady=(0,5))
        if self.configuration.sounds_capture['enable']:
            self.sounds_capture_enable_combobox.current(1)
        else:
            self.sounds_capture_enable_combobox.current(0)

        self.sounds_capture_enable_set_button = tk.Button(sounds_capture_subframe_1, text='Save', command=self.save_sounds_capture_enable, font=self.font)
        self.sounds_capture_enable_set_button.pack(side=tk.RIGHT, padx=(0,5), pady=(0,5))

        self.sounds_capture_suspend_button_str = tk.StringVar()
        self.sounds_capture_running_label_str = tk.StringVar()

        if pi.read(SHUTDOWN_PIN) == 1:
            self.sounds_capture_suspend_button_str.set('Resume')
            self.sounds_capture_running_label_str.set('Stopped (reboot the system to restart)')
            bg = 'red'
        else:
            if pi.read(SOUNDS_CAPTURE_ACTIVITY_PIN) == 1:
                self.sounds_capture_suspend_button_str.set('Resume')
                self.sounds_capture_running_label_str.set('Suspended (click on Resume to restart)')
                bg = 'orange'
            else:
                self.sounds_capture_suspend_button_str.set('Suspend')
                self.sounds_capture_running_label_str.set('Running (click on Suspend to pause)')
                bg = 'green'

        self.sounds_capture_running_canvas = tk.Canvas(sounds_capture_subframe_2, width=15, height=15)
        self.sounds_capture_running_canvas.pack(side=tk.LEFT, padx=(5,5))

        self.sounds_capture_running_state = self.sounds_capture_running_canvas.create_oval(1, 1, 15, 15, fill=bg, outline=bg)

        self.sounds_capture_running_label = tk.Label(sounds_capture_subframe_2, textvariable=self.sounds_capture_running_label_str, font=self.font)
        self.sounds_capture_running_label.pack(side=tk.LEFT, padx=(5,5))

        self.sounds_capture_stop_button = tk.Button(sounds_capture_subframe_2, text='Stop', command=self.stop_captures, font=self.font)
        self.sounds_capture_stop_button.pack(side=tk.RIGHT, padx=(0,5), pady=(0,5))

        self.sounds_capture_suspend_button = tk.Button(sounds_capture_subframe_2, textvariable=self.sounds_capture_suspend_button_str, command=self.manage_sounds_capture, font=self.font)
        self.sounds_capture_suspend_button.pack(side=tk.RIGHT, padx=(0,5), pady=(0,5))

        self.sounds_capture_duration_label = tk.Label(sounds_capture_subframe_3, text='Recording duration (s)', font=self.font)
        self.sounds_capture_duration_label.pack(side=tk.LEFT, padx=(5,5))

        self.sounds_capture_duration_entry = tk.Entry(sounds_capture_subframe_3, width=TK_ENTRY_WIDTH, font=self.font)
        self.sounds_capture_duration_entry.insert(0, str(self.configuration.sounds_capture['duration']))
        self.sounds_capture_duration_entry.pack(side=tk.LEFT, padx=(5,5))

        self.sounds_capture_duration_set_button = tk.Button(sounds_capture_subframe_3, text='Save', command=self.save_sounds_capture_duration, font=self.font)
        self.sounds_capture_duration_set_button.pack(side=tk.RIGHT, padx=(0,5), pady=(0,5))

        if pi.read(SHUTDOWN_PIN) == 1:
            self.sounds_capture_stop_button.configure(state=tk.DISABLED)
            self.sounds_capture_suspend_button.configure(state=tk.DISABLED)
        else:
            if pi.read(SOUNDS_CAPTURE_ACTIVITY_PIN) == 0:
                self.sounds_capture_duration_entry.configure(state=tk.DISABLED)
                self.sounds_capture_duration_set_button.configure(state=tk.DISABLED)

        # Raspberry Pi
        rpi_label_frame = tk.LabelFrame(left_frame, text='Raspberry Pi', font=self.font)
        rpi_label_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=(5,5), pady=(0,5))

        rpi_subframe_1 = tk.Frame(rpi_label_frame)
        rpi_subframe_1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        rpi_subframe_2 = tk.Frame(rpi_label_frame)
        rpi_subframe_2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        rpi_subframe_3 = tk.Frame(rpi_label_frame)
        rpi_subframe_3.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        rpi_model_label = tk.Label(rpi_subframe_1, text='Model: ' + self.rpi.model, font=self.font)
        rpi_model_label.pack(side=tk.TOP, padx=(5,5), anchor='w')
        rpi_revision_label = tk.Label(rpi_subframe_1, text='Revision: ' + self.rpi.revision, font=self.font)
        rpi_revision_label.pack(side=tk.TOP, padx=(5,5), anchor='w')
        rpi_serial_label = tk.Label(rpi_subframe_1, text='Serial: ' + self.rpi.serial, font=self.font)
        rpi_serial_label.pack(side=tk.TOP, padx=(5,5), anchor='w')
        rpi_hostname_label = tk.Label(rpi_subframe_2, text='Hostname: ' + self.rpi.hostname, font=self.font)
        rpi_hostname_label.pack(side=tk.TOP, padx=(5,5), anchor='w')
        rpi_wifi_label = tk.Label(rpi_subframe_2, text='WiFi: ' + self.rpi.wifi_ssid, font=self.font)
        rpi_wifi_label.pack(side=tk.TOP, padx=(5,5), anchor='w')
        rpi_ip_label = tk.Label(rpi_subframe_2, text='IP: ' + self.rpi.ip_address, font=self.font)
        rpi_ip_label.pack(side=tk.TOP, padx=(5,5), pady=(0,5), anchor='w')
        self.rpi_temp_str = tk.StringVar()
        self.rpi_temp_str.set(f"Temperature: {self.rpi.get_temperature():.1f} \u00B0C (must be less than 80 \u00B0C)")
        rpi_temperature_label = tk.Label(rpi_subframe_1, textvariable=self.rpi_temp_str, font=self.font)
        rpi_temperature_label.pack(side=tk.TOP, padx=(5,5), anchor='w')

        # Storage
        storage_label_frame = tk.LabelFrame(left_frame, text='Storage', font=self.font)
        storage_label_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=(5,5), pady=(0,5))

        storage_data_path_label = tk.Label(storage_label_frame, text='Data path: ' + SAVE_FOLDER, font=self.font)
        storage_data_path_label.pack(side=tk.TOP, padx=(5,5), anchor='w')

        if SAVE_FOLDER.startswith('/home'):
            output = subprocess.check_output(['df', '-h', '/']).decode('utf-8').split('\n')[1].split()
        else:
            output = subprocess.check_output(['df', '-h', self.external_drive.path]).decode('utf-8').split('\n')[1].split()

        self.storage_data_stats_str = tk.StringVar()
        self.storage_data_stats_str.set(f'Total: {output[1]} - Used: {output[2]} - Available: {output[3]} - Used: {output[4]}')

        storage_data_stats_label = tk.Label(storage_label_frame, textvariable=self.storage_data_stats_str, font=self.font)
        storage_data_stats_label.pack(side=tk.TOP, padx=(5,5), pady=(0,5), anchor='w')

        # # Environment
        # environment_label_frame = tk.LabelFrame(left_frame, text='Environment')
        # environment_label_frame.pack(side=tk.TOP, fill=tk.X, padx=(5,5), pady=(0,5))

        # environment_subframe_1 = tk.Frame(environment_label_frame)
        # environment_subframe_1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # environment_subframe_2 = tk.Frame(environment_label_frame)
        # environment_subframe_2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # nowsec = datetime.now().second

        # if nowsec < 55 or nowsec > 5:
            # sht31 = SHT31()
            # wittypi = WittyPi()
        # else:
            # sht31.temperature = -99.0
            # sht31.humidity = -99.0
            # wittypi.input_voltage = 0.0
            # wittypi.output_voltage = 0.0
            # wittypi.output_current = 0.0

        # self.ext_temp_label = tk.Label(environment_subframe_1, text=f'Ext. Temp. (C): {sht31.temperature:.1f}')
        # self.ext_temp_label.pack(side=tk.TOP, padx=(5,5), anchor='w')
        # self.ext_hum_label = tk.Label(environment_subframe_1, text=f'Ext. Hum. (%) {sht31.humidity:.1f}')
        # self.ext_hum_label.pack(side=tk.TOP, padx=(5,5), anchor='w')

        # self.vin_power_label = tk.Label(environment_subframe_2, text=f'Vin (V): {wittypi.input_voltage}')
        # self.vin_power_label.pack(side=tk.TOP, padx=(5,5), anchor='w')
        # self.vout_power_label = tk.Label(environment_subframe_2, text=f'Vout (V): {wittypi.output_voltage}')
        # self.vout_power_label.pack(side=tk.TOP, padx=(5,5), anchor='w')
        # self.iout_power_label = tk.Label(environment_subframe_2, text=f'Iout (A): {wittypi.output_current}')
        # self.iout_power_label.pack(side=tk.TOP, padx=(5,5), anchor='w')

        # self.ext_temp_label = tk.Label(environment_subframe_1, text=f'Ext. Temp. (C): {0.0:.1f}')
        # self.ext_temp_label.pack(side=tk.TOP, padx=(5,5), anchor='w')
        # self.ext_hum_label = tk.Label(environment_subframe_1, text=f'Ext. Hum. (%) {0.0:.1f}')
        # self.ext_hum_label.pack(side=tk.TOP, padx=(5,5), anchor='w')

        # self.vin_power_label = tk.Label(environment_subframe_2, text=f'Vin (V): {0.0}')
        # self.vin_power_label.pack(side=tk.TOP, padx=(5,5), anchor='w')
        # self.vout_power_label = tk.Label(environment_subframe_2, text=f'Vout (V): {0.0}')
        # self.vout_power_label.pack(side=tk.TOP, padx=(5,5), anchor='w')
        # self.iout_power_label = tk.Label(environment_subframe_2, text=f'Iout (A): {0.0}')
        # self.iout_power_label.pack(side=tk.TOP, padx=(5,5), anchor='w')

        # Configuration scrolltext
        self.configuration_scolltext = scrolledtext.ScrolledText(right_frame, font=self.font)
        self.configuration_scolltext.pack(fill=tk.BOTH, expand=True, pady=(5,0), padx=(0,5))
        self.update_configuration_display()

    def save_schedule_enable(self):

        if self.schedule_enable_combobox.get() == 'True':

            self.configuration.schedule['enable'] = True
            wakeup_hours = self.schedule_wakeup_hours_combobox.get()
            wakeup_minutes = self.schedule_wakeup_minutes_combobox.get()

            self.configuration.schedule['wakeup'] = wakeup_hours + ':' + wakeup_minutes

            sleep_hours = self.schedule_sleep_hours_combobox.get()
            sleep_minutes = self.schedule_sleep_minutes_combobox.get()

            self.configuration.schedule['sleep'] = sleep_hours + ':' + sleep_minutes

            self.scheduler.set(int(wakeup_hours), int(wakeup_minutes), int(sleep_hours), int(sleep_minutes))

            self.scheduler.enable()

        else:

            self.scheduler.disable()
            self.configuration.schedule['enable'] = False

        self.configuration.save()

        self.configuration.read()

        self.update_configuration_display()

        self.status_text.set(f"New configuration saved: scheduler {'ebabled' if self.configuration.schedule['enable'] else 'disabled'}")

        logger.info(f"{this_script}: scheduler {'ebabled' if self.configuration.schedule['enable'] else 'disabled'}")

    def save_schedule_time(self):

        wakeup_hours = self.schedule_wakeup_hours_combobox.get()
        wakeup_minutes = self.schedule_wakeup_minutes_combobox.get()

        self.configuration.schedule['wakeup'] = wakeup_hours + ':' + wakeup_minutes

        sleep_hours = self.schedule_sleep_hours_combobox.get()
        sleep_minutes = self.schedule_sleep_minutes_combobox.get()

        self.configuration.schedule['sleep'] = sleep_hours + ':' + sleep_minutes

        self.configuration.save()

        self.configuration.read()

        self.update_configuration_display()

        self.scheduler.set(int(wakeup_hours), int(wakeup_minutes), int(sleep_hours), int(sleep_minutes), None, None)
        self.scheduler.save()

        output = self.scheduler.runScript()

        outputs = output.decode('utf-8').split('\n')

        for output in outputs:
            if output:
                logger.info(f'{this_script}: ' + output)

        self.status_text.set(f'New configuration saved: wake-up time set to {wakeup_hours}:{wakeup_minutes} and sleep time set to {sleep_hours}:{sleep_minutes}')

        logger.info(f'{this_script}: wake-up time set to {wakeup_hours}:{wakeup_minutes} and sleep time set to {sleep_hours}:{sleep_minutes}')

    def save_schedule_on_off(self):

        on_duration = self.schedule_on_duration_entry.get()
        off_duration = self.schedule_off_duration_entry.get()

        try:

            on_duration = int(on_duration)
            off_duration = int(off_duration)

            if on_duration > 0 and off_duration > 0:

                self.configuration.schedule['on_duration'] = on_duration
                self.configuration.schedule['off_duration'] = off_duration

                self.configuration.save()

                self.configuration.read()

                self.update_configuration_display()

                self.status_text.set(f'New configuration saved: on duration set to {on_duration} minutes and off duration set to {off_duration} minutes')
                logger.info(f'{this_script}: on duration set to {on_duration} minutes and off duration set to {off_duration} minutes')

            else:

                self.schedule_on_duration_entry.delete('0', tk.END)
                self.schedule_on_duration_entry.insert(tk.END, self.configuration.schedule['on_duration'])
                self.schedule_off_duration_entry.delete('0', tk.END)
                self.schedule_off_duration_entry.insert(tk.END, self.configuration.schedule['off_duration'])
                self.status_text.set('Error: time step and duration must be positive integers greater than 0')
                logger.error(f'{this_script}: ' + 'time step and duration must be positive integers greater than 0')

        except BaseException as e:

            self.schedule_on_duration_entry.delete('0', tk.END)
            self.schedule_on_duration_entry.insert(tk.END, self.configuration.schedule['on_duration'])
            self.schedule_off_duration_entry.delete('0', tk.END)
            self.schedule_off_duration_entry.insert(tk.END, self.configuration.schedule['off_duration'])
            self.status_text.set('Error: time step and duration must be positive integers greater than 0')

            logger.error(f'{this_script}: ' + 'time step and duration must be positive integers greater than 0')
            logger.error(f'{this_script}: ' + str(e))


    def save_images_capture_enable(self):

        if self.images_capture_enable_combobox.get() == 'True':
            self.configuration.images_capture['enable'] = True
        else:
            self.configuration.images_capture['enable'] = False

        self.configuration.save()

        self.configuration.read()

        self.update_configuration_display()

        self.status_text.set(f"New configuration saved: images capture {'enabled' if self.configuration.images_capture['enable'] else 'disabled'}")
        logger.info(f"{this_script}: images capture {'enabled' if self.configuration.images_capture['enable'] else 'disabled'}")

    def stop_captures(self):

        answer = askyesno(title='Confirmation', message="This will stop both images and sounds capture. You'll have to reboot the system to start them again.\n\nStop the process?")

        if answer:

            self.status_text.set(f'Wait {DELAY_BEFORE_SHUTDOWN} seconds')

            self.update()

            pi.write(SHUTDOWN_PIN, 1)

            sleep(DELAY_BEFORE_SHUTDOWN)

            self.images_capture_running_label_str.set('Stopped (reboot the system to restart)')
            self.sounds_capture_running_label_str.set('Stopped (reboot the system to restart)')

            self.images_capture_stop_button.configure(state=tk.DISABLED)
            self.sounds_capture_stop_button.configure(state=tk.DISABLED)

            self.images_capture_suspend_button.configure(state=tk.DISABLED)
            self.sounds_capture_suspend_button.configure(state=tk.DISABLED)

            self.images_capture_running_canvas.itemconfig(self.images_capture_running_state, fill='red', outline='red')
            self.sounds_capture_running_canvas.itemconfig(self.sounds_capture_running_state, fill='red', outline='red')

            self.status_text.set('Images and sounds capture stopped. Reboot the system to start them again')
            logger.info(f'{this_script}: images and sounds capture stopped')

    def manage_images_capture(self):

        if pi.read(IMAGES_CAPTURE_ACTIVITY_PIN) == 0:

            pi.write(IMAGES_CAPTURE_ACTIVITY_PIN, 1)
            self.images_capture_suspend_button_str.set('Resume')
            self.images_capture_running_label_str.set('Suspended (click on Resume to restart)')
            self.images_capture_running_canvas.itemconfig(self.images_capture_running_state, fill='orange', outline='orange')
            self.images_capture_time_step_set_button.configure(state=tk.NORMAL)
            self.images_capture_time_step_entry.configure(state=tk.NORMAL)
            self.status_text.set('Images capture suspended')
            logger.info(f'{this_script}: images capture suspended')

        else:

            pi.write(IMAGES_CAPTURE_ACTIVITY_PIN, 0)
            self.images_capture_suspend_button_str.set('Suspend')
            self.images_capture_running_label_str.set('Running')
            self.images_capture_running_canvas.itemconfig(self.images_capture_running_state, fill='green', outline='green')
            self.images_capture_time_step_set_button.configure(state=tk.DISABLED)
            self.images_capture_time_step_entry.configure(state=tk.DISABLED)
            self.status_text.set('Images capture resumed')
            logger.info(f'{this_script}: images capture resumed')

    def save_images_capture_time_step(self):

        time_step = self.images_capture_time_step_entry.get()

        try:

            time_step = int(time_step)

            if time_step > 0:

                self.configuration.images_capture['time_step'] = time_step

                self.configuration.save()

                self.configuration.read()

                self.update_configuration_display()

                self.status_text.set(f'New configuration saved: image capture time step set to {time_step} seconds')
                logger.info(f'{this_script}: image capture time step set to {time_step} seconds')

            else:

                self.images_capture_time_step_entry.delete('0', tk.END)
                self.images_capture_time_step_entry.insert(tk.END, self.configuration.images_capture['time_step'])
                self.status_text.set('Error: time step must be a positive integer greater than 0')
                logger.error(f'{this_script}: ' + 'time step must be a positive integer greater than 0')

        except BaseException as e:

            self.images_capture_time_step_entry.delete('0', tk.END)
            self.images_capture_time_step_entry.insert(tk.END, self.configuration.images_capture['time_step'])
            self.status_text.set('Error: time step must be a positive integer greater than 0')

            logger.error(f'{this_script}: ' + 'time step must be a positive integer greater than 0')
            logger.error(f'{this_script}: ' + str(e))

    def save_site_id(self):

        site_id = self.site_id_entry.get()

        self.configuration.site['id'] = site_id

        self.configuration.save()

        self.configuration.read()

        self.update_configuration_display()

        self.status_text.set(f'New configuration saved: site ID set to {site_id}')
        logger.info(f'{this_script}: site ID set to {site_id}')

    def save_sounds_capture_enable(self):

        if self.sounds_capture_enable_combobox.get() == 'True':
            self.configuration.sounds_capture['enable'] = True
        else:
            self.configuration.sounds_capture['enable'] = False

        self.configuration.save()

        self.configuration.read()

        self.update_configuration_display()

        self.status_text.set(f"New configuration saved: sounds capture {'enabled' if self.configuration.sounds_capture['enable'] else 'disabled'}")
        logger.info(f"{this_script}: sounds capture {'enabled' if self.configuration.sounds_capture['enable'] else 'disabled'}")

    def manage_sounds_capture(self):

        if pi.read(SOUNDS_CAPTURE_ACTIVITY_PIN) == 0:

            pi.write(SOUNDS_CAPTURE_ACTIVITY_PIN, 1)
            self.sounds_capture_suspend_button_str.set('Resume')
            self.sounds_capture_running_label_str.set('Suspended (click on Resume to restart)')
            self.sounds_capture_running_canvas.itemconfig(self.sounds_capture_running_state, fill='orange', outline='orange')
            self.sounds_capture_duration_set_button.configure(state=tk.NORMAL)
            self.sounds_capture_duration_entry.configure(state=tk.NORMAL)
            self.status_text.set('Sounds capture suspended')
            logger.info(f'{this_script}: sounds capture suspended')

        else:

            pi.write(SOUNDS_CAPTURE_ACTIVITY_PIN, 0)
            self.sounds_capture_suspend_button_str.set('Suspend')
            self.sounds_capture_running_label_str.set('Running')
            self.sounds_capture_running_canvas.itemconfig(self.sounds_capture_running_state, fill='green', outline='green')
            self.sounds_capture_duration_set_button.configure(state=tk.DISABLED)
            self.sounds_capture_duration_entry.configure(state=tk.DISABLED)
            self.status_text.set('Sounds capture resumed')
            logger.info(f'{this_script}: sounds capture resumed')

    def save_sounds_capture_duration(self):

        duration = self.sounds_capture_duration_entry.get()

        try:

            duration = int(duration)

            if duration > 0:

                self.configuration.sounds_capture['duration'] = int(duration)

                self.configuration.save()

                self.configuration.read()

                self.update_configuration_display()

                self.status_text.set(f'New configuration saved: sounds capture duration set to {duration} seconds')
                logger.info(f'{this_script}: sounds capture duration set to {duration} seconds')

            else:

                self.sounds_capture_duration_entry.delete('0', tk.END)
                self.sounds_capture_duration_entry.insert(tk.END, self.configuration.sounds_capture['duration'])
                self.status_text.set('Error: duration must be a positive integer greater than 0')
                logger.error('Error: duration must be a positive integer greater than 0')

        except BaseException as e:
            self.sounds_capture_duration_entry.delete('0', tk.END)
            self.sounds_capture_duration_entry.insert(tk.END, self.configuration.sounds_capture['duration'])
            self.status_text.set('Error: duration must be a positive integer greater than 0')

            logger.error(f'{this_script}: ' + 'duration must be a positive integer greater than 0')
            logger.error(f'{this_script}: ' + str(e))


    def save_laser_enable(self):

        if self.laser_enable_combobox.get() == 'True':
            self.configuration.laser['enable'] = True
        else:
            self.configuration.laser['enable'] = False

        self.configuration.save()

        self.configuration.read()

        self.update_configuration_display()

        self.status_text.set(f"New configuration saved: laser {'enabled' if self.configuration.laser['enable'] else 'disabled'}")
        logger.info(f"{this_script}: laser {'enabled' if self.configuration.laser['enable'] else 'disabled'}")


    def update_configuration_display(self):

        configuration = self.configuration.to_string()

        s = configuration.find('Ai detection\n')
        e = configuration.find('Images capture\n')

        configuration = configuration[:s] + configuration[e:]

        s = configuration.find('Laser\n')
        e = configuration.find('Schedule\n')

        configuration = configuration[:s] + configuration[e:]

        self.configuration_scolltext.configure(state=tk.NORMAL)
        self.configuration_scolltext.delete('0.0', tk.END)
        self.configuration_scolltext.insert(tk.END, configuration)
        self.configuration_scolltext.configure(state=tk.DISABLED)

    def update_ui(self):

        try:

            if time() - self.last_time_ext_disk > EXT_DISK_INTERVAL:

                self.last_time_ext_disk = time()

                if SAVE_FOLDER.startswith('/home'):
                    output = subprocess.check_output(['df', '-h', '/']).decode('utf-8').split('\n')[1].split()
                else:
                    output = subprocess.check_output(['df', '-h', self.external_drive.path]).decode('utf-8').split('\n')[1].split()

                self.storage_data_stats_str.set(f'Total: {output[1]} - Used: {output[2]} - Available: {output[3]} - Used %: {output[4]}')

            if time() - self.last_time_cpu_temp > CPU_TEMP_INTERVAL:

                self.last_time_cpu_temp = time()

                self.rpi_temp_str.set(f"Temperature: {self.rpi.get_temperature():.1f} \u00B0C (must be less than 80 \u00B0C)")

        except BaseException as e:

            logger.error(f'{this_script}: ' + str(e))

        self.after(REFRESH_UI_INTERVAL_IN_MS, self.update_ui)

def run():

    logger.info(f'{this_script}: start')

    tk_interface = TkInterface()
    tk_interface.after(REFRESH_UI_INTERVAL_IN_MS, tk_interface.update_ui)
    tk_interface.mainloop()

if __name__ == '__main__':

    run()

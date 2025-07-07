#! /usr/bin/python3
import os

from PIL import Image, ImageTk
from datetime import datetime

from threading import Thread
from queue import Queue

from time import sleep

import logging

import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
from tkinter import messagebox
from tkinter.font import Font

from functools import partial

from json import dump

import cv2
import time
import libcamera

from configuration import Configuration

from peripherals.camera import Camera
from peripherals.leds import Leds
from peripherals.pinout import LEDS_REAR_PIN, LEDS_FRONT_PIN, LEDS_UV_PIN, LEDS_DEPORTED_PIN
from peripherals.rpi import Rpi

this_script = os.path.basename(__file__)[:-3]

AI_ENABLE = False

rpi = Rpi()
if rpi.os_version == '64-bit' and AI_ENABLE:
    AI_AVAILABLE = True
    from ultralytics import YOLO
else:
    AI_AVAILABLE = False

from globals_parameters import AI_MODEL, PYTHON_SCRIPTS_BASE_FOLDER, IMAGES_CAPTURE_FOLDER, LOGS_FOLDER, TODAY

logger = logging.getLogger('main')
filename = os.path.join(LOGS_FOLDER, TODAY + '_' + this_script + '.log')
logging.basicConfig(filename=filename,
                    format='%(asctime)s;%(levelname)s;"%(message)s"',
                    encoding='utf-8',
                    datefmt='%d/%m/%Y;%H:%M:%S',
                    level=logging.DEBUG)


VERSION = '1.0.0'

TK_WINDOWS_TITLE = 'Entomoscope - Images Capture Settings - v' + VERSION

TK_WINDOW_WIDTH_IN_PX = 1500
TK_WINDOW_HEIGHT_IN_PX = 950

TK_ENTRY_WIDTH = 8
TK_COMBOBOX_WIDTH = 15
TK_SCALE_WIDTH = 275

UPDATE_UI_INTERVAL_IN_MS = 50

EXPOSURE_TIME_MAX = 50000

AVAILABLE_COLOR = 'black'
NOT_AVAILABLE_COLOR = 'thistle4'

SHOW_PERF = False

DISPLAY_MAIN_FRAME = False

CPU_TEMP_INTERVAL = 5

DELAY_LEDS_ON_OFF_MANUAL_EXPOSURE_IN_S = 0.5
DELAY_LEDS_ON_OFF_AUTO_EXPOSURE_IN_S = 1

global image_tk_3 # Workaround

class TkInterface(tk.Tk):

    def __init__(self):

        tk.Tk.__init__(self)

        self.title(TK_WINDOWS_TITLE)
        self.geometry(f'{TK_WINDOW_WIDTH_IN_PX}x{TK_WINDOW_HEIGHT_IN_PX}')
        self.protocol("WM_DELETE_WINDOW", self.close_window)

        self.TK_IMAGE_HEIGHT_MAX = 500
        self.TK_IMAGE_WIDTH_MAX = 888

        self.font = Font(font='Consolas')
        self.font.config(size=8)

        self.font_2 = Font(font='Consolas')
        self.font_2.config(size=8)

        self.font_arrows = Font(font='Consolas')
        self.font_arrows.config(size=10)

        style = ttk.Style()
        style.configure('TNotebook.Tab', font=self.font, padding=[5, 5])

        self.option_add('*TCombobox*Listbox.font', self.font)

        self.configuration = Configuration()

        self.leds_rear = Leds(LEDS_REAR_PIN)
        self.leds_front = Leds(LEDS_FRONT_PIN)
        self.leds_uv = Leds(LEDS_UV_PIN)
        self.leds_deported = Leds(LEDS_DEPORTED_PIN)

        self.preview_scale = 1

        self.camera = Camera(configuration=self.configuration, mode='preview')

        if self.camera.available:

            if not self.camera.is_camera_supported:

                # TODO
                print('Wrong camera')

                if self.camera.model == 'imx708':
                    model = 'v3'
                elif self.camera.model == 'imx219':
                    model = 'v2'
                elif self.camera.model == 'ov5647':
                    model = 'v1'
                elif self.camera.model == 'imx477':
                    model = 'hq'

                response = messagebox.askyesno(title='Camera choice?', message=f"Camera found ({model} - {self.camera.model}) don't match camera in configuration file ({self.configuration.camera['model']})\n\nUpdate configuration file?")

                if response:

                    self.configuration.camera['model'] = model

                    self.configuration.save()

                    self.configuration.read()

                    self.camera.configure(self.configuration)

        self.create_widgets()

        if AI_AVAILABLE and AI_ENABLE:
            self.ai_model = YOLO(AI_MODEL) # load .pt file

        self.crop_limits = self.configuration.camera['sensor']['crop_limits']

        if self.camera.available:

            self.camera.start()

            if self.camera.started:
                self.camera.available = True
            else:
                self.camera.available = False

        self.take_photo = False
        self.take_photo_flash = False

        self.last_time = time.time()

        self.ai_boxes_color = [(255,85,0), (255,170,0), (255,255,0), (170,255,85), (85,255,170), (0,255,255), (0,170,255), (0,85,255), (0,0,255), (0,0,170)]

        self.last_time_cpu_temp = time.time()

        self.image_queue = Queue()
        self.image_lock = False
        self.capture_thread = Thread(target=self.capture_image, daemon=True)
        self.capture_thread.start()

        self.status_text.set('Ready')

        self.update()

        self.after(UPDATE_UI_INTERVAL_IN_MS, self.update_ui)

    def close_window(self):

        self.leds_rear.turn_off()
        self.leds_front.turn_off()
        self.leds_uv.turn_off()
        self.leds_deported.turn_off()

        if self.camera.available:
            self.camera.stop()

        self.quit()

    def capture_image(self):

        global image_tk_3 # Workaround

        while True:
            
            sleep(0.05)

            if self.camera.available and not self.image_lock:

                if SHOW_PERF:
                    start_time = time.perf_counter_ns()
                    
                if self.take_photo:
                    print('Capture')
               
                if self.take_photo_flash:
                    print('Capture + Flash')
                     
                if self.take_photo_flash:
                    
                    if self.configuration.leds['mode'] == 1:
                        self.leds_rear.set_intensity(self.configuration.leds['intensity_rear'])
                        self.leds_rear.turn_on()
                    if self.configuration.leds['mode'] == 1 or configuration.leds['mode'] == 2:
                        self.leds_front.set_intensity(self.configuration.leds['intensity_front'])
                        self.leds_front.turn_on()
                    if self.configuration.leds['mode'] == 3:
                        self.leds_deported.set_intensity(self.configuration.leds['intensity_deported'])
                        self.leds_deported.turn_on()
                        
                    if self.configuration.leds['delay_on']:                
                        sleep(self.configuration.leds['delay_on'])

                self.camera.capture(get_metadata=True, flush=False)

                if self.take_photo_flash:
                    
                    if self.configuration.leds['delay_off']:                
                        sleep(self.configuration.leds['delay_off'])
                    
                    if self.configuration.leds['mode'] == 1:
                        self.leds_rear.turn_off()
                    if self.configuration.leds['mode'] == 1 or configuration.leds['mode'] == 2:
                        self.leds_front.turn_off()
                    if self.configuration.leds['mode'] == 3:
                        self.leds_deported.turn_off()
                    
                if SHOW_PERF:
                    print(f'Capture {(time.perf_counter_ns() - start_time)/1E9}')
                    start_time = time.perf_counter_ns()

                if DISPLAY_MAIN_FRAME:
                    image = cv2.cvtColor(self.camera.frame_data_main , cv2.COLOR_BGR2RGB)
                else:
                    image = cv2.cvtColor(self.camera.frame_data_lores , cv2.COLOR_BGR2RGB)

                if SHOW_PERF:
                    print(f'Color {(time.perf_counter_ns() - start_time)/1E9}')
                    start_time = time.perf_counter_ns()

                image_width = image.shape[1]
                image_height = image.shape[0]

                if AI_AVAILABLE and AI_ENABLE and self.ai_enable.get():

                    prediction = self.ai_model.predict(self.camera.frame_data_lores, imgsz=(self.configuration.ai_detection['image_width'], self.configuration.ai_detection['image_height']), conf=self.configuration.ai_detection['min_confidence'], show=False, save=False, save_txt=False, verbose=False)[0]

                    if SHOW_PERF:
                        print(f'Predict {(time.perf_counter_ns() - start_time)/1E9}')
                        start_time = time.perf_counter_ns()

                    insect_detected = len(prediction.boxes) > 0

                    if insect_detected is True:

                        speed = prediction.speed['preprocess'] + prediction.speed['inference'] + prediction.speed['postprocess']
                        self.ai_speed.set(f'Speed: {speed:.0f} ms')

                        idx_color = 0
                        for box in prediction.boxes:
                            box_lists = box.xywhn.tolist()
                            for box_list in box_lists:
                                x, y, w, h = int(box_list[0] * image_width), int(box_list[1] * image_height), int(box_list[2] * image_width), int(box_list[3] * image_height)
                                image = cv2.rectangle(image, (int(x-w/2),int(y-h/2)), (int(x+w/2),int(y+h/2)), self.ai_boxes_color[idx_color], 2)
                                idx_color += 1
                                if idx_color > len(self.ai_boxes_color):
                                    idx_color = 0

                        if self.save_ai_capture.get():

                            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                            jpeg_data = cv2.imencode('.jpg', image, [int(cv2.IMWRITE_JPEG_QUALITY), self.configuration.files['jpeg_quality']])[1].tobytes()
                            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

                            now_str = datetime.now().strftime('%Y%m%d%H%M%S')

                            jpeg_file_path = os.path.join(IMAGES_CAPTURE_FOLDER, now_str + '_settings.jpg')

                            with open(jpeg_file_path, 'wb') as f:
                                f.write(jpeg_data)

                            extra_metadata = {'SiteID': self.configuration.site['id'], 'Latitude': self.configuration.gnss['latitude'], 'Longitude': self.configuration.gnss['longitude']}

                            metadata = {}
                            metadata.update(self.camera.metadata)
                            metadata.update(extra_metadata)

                            json_file_path = jpeg_file_path.replace('.jpg', '.json')

                            with open(json_file_path, 'w') as f:
                                dump(metadata, f, indent=4, sort_keys=True, separators=(',', ': '))

                        if SHOW_PERF:
                            print(f'Box {(time.perf_counter_ns() - start_time)/1E9}')
                            start_time = time.perf_counter_ns()

                # image_width = image.shape[1]
                # image_height = image.shape[0]

                # if image_height > self.TK_IMAGE_HEIGHT_MAX and image_width > self.TK_IMAGE_WIDTH_MAX:

                    # scale_width = self.TK_IMAGE_WIDTH_MAX / image_width
                    # scale_height = self.TK_IMAGE_HEIGHT_MAX / image_height

                    # scale = scale_width if scale_width < scale_height else scale_height

                    # new_width = int(image_width * scale)
                    # new_height = int(image_height * scale)

                # elif image_height > self.TK_IMAGE_HEIGHT_MAX:

                    # scale = self.TK_IMAGE_HEIGHT_MAX / image_height

                    # new_width = int(image_width * scale)
                    # new_height = self.TK_IMAGE_HEIGHT_MAX

                # elif image_width > self.TK_IMAGE_WIDTH_MAX:

                    # scale = self.TK_IMAGE_WIDTH_MAX / image_width

                    # new_height = int(image_height * scale)
                    # new_width = self.TK_IMAGE_HEIGHT_MAX

                # else:

                    # scale_width = self.TK_IMAGE_WIDTH_MAX / image_width
                    # scale_height = self.TK_IMAGE_HEIGHT_MAX / image_height

                    # scale = scale_width if scale_width < scale_height else scale_height

                    # new_width = int(image_width * scale)
                    # new_height = int(image_height * scale)

                # image = cv2.resize(image, (new_width, new_height))

                if self.take_photo or self.take_photo_flash:

                    extra_metadata = {'SiteID': self.configuration.site['id'], 'Latitude': self.configuration.gnss['latitude'], 'Longitude': self.configuration.gnss['longitude']}

                    # if DISPLAY_MAIN_FRAME:
                        # jpeg_data = cv2.imencode('.jpg', self.camera.frame_data_main, [int(cv2.IMWRITE_JPEG_QUALITY), self.configuration.files['jpeg_quality']])[1].tobytes()
                    # else:
                        # jpeg_data = cv2.imencode('.jpg', self.camera.frame_data_lores, [int(cv2.IMWRITE_JPEG_QUALITY), self.configuration.files['jpeg_quality']])[1].tobytes()

                    jpeg_data = cv2.imencode('.jpg', self.camera.frame_data_main, [int(cv2.IMWRITE_JPEG_QUALITY), self.configuration.files['jpeg_quality']])[1].tobytes()

                    now_str = datetime.now().strftime('%Y%m%d%H%M%S')
                    
                    if self.take_photo:
                        jpeg_file_path = os.path.join(IMAGES_CAPTURE_FOLDER, now_str + '_settings_capture.jpg')
                    elif self.take_photo_flash:
                        jpeg_file_path = os.path.join(IMAGES_CAPTURE_FOLDER, now_str + '_settings_capture_flash.jpg')

                    with open(jpeg_file_path, 'wb') as f:
                        f.write(jpeg_data)

                    metadata = {}
                    metadata.update(self.camera.metadata)
                    metadata.update(extra_metadata)

                    json_file_path = jpeg_file_path.replace('.jpg', '.json')

                    with open(json_file_path, 'w') as f:
                        dump(metadata, f, indent=4, sort_keys=True, separators=(',', ': '))

                    self.take_photo = False
                    self.take_photo_flash = False

                    self.status_text.set('Image saved to ' + jpeg_file_path)

                image_tk = Image.fromarray(image)

                self.image_tk_2 = ImageTk.PhotoImage(image_tk)

                self.image_lock = True

    def create_widgets(self):

        # Bottom frame
        bottom_frame = tk.Frame(self)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, expand=False)

        self.status_text = tk.StringVar()
        self.status_text.set('Initializing...')
        self.status_label = tk.Label(bottom_frame, textvariable=self.status_text, bg='white', font=self.font)
        self.status_label.pack(fill=tk.X, expand=True, pady=(0,0))

        # Right frame
        right_frame = tk.Frame(self)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Configuration scrolltext
        self.configuration_scolltext = scrolledtext.ScrolledText(right_frame, width=18, font=self.font_2)
        self.configuration_scolltext.pack(fill=tk.BOTH, expand=True, pady=(5,5), padx=(0,5))
        self.update_configuration_display()

        # Left top frame
        left_top_frame = tk.Frame(self, width=self.TK_IMAGE_WIDTH_MAX + 10, height=self.TK_IMAGE_HEIGHT_MAX + 10)
        left_top_frame.pack(side=tk.TOP)

        # Preview
        self.image_tk = Image.open(os.path.join(PYTHON_SCRIPTS_BASE_FOLDER, 'images', 'no-video-640x360.png'))
        self.no_video_image_tk = ImageTk.PhotoImage(self.image_tk)
        self.image_tk_2 = ImageTk.PhotoImage(self.image_tk)

        self.preview_label = tk.Label(left_top_frame, image=self.no_video_image_tk)
        self.preview_label.pack(pady=(5,5))

        # Left bottom frame
        left_bottom_frame = tk.Frame(self)
        left_bottom_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        notebook = ttk.Notebook(left_bottom_frame)

        # Info
        self.info_frame = tk.Frame(notebook)
        self.info_frame.pack(side=tk.TOP, padx=(5,5), pady=(5,5), anchor='w')

        notebook.add(self.info_frame, text ='Info')

        camera_model_label = tk.Label(self.info_frame, text=f"Camera model: {self.configuration.camera['model']}", font=self.font)
        camera_model_label.pack(side=tk.TOP, padx=(5,0), pady=(5,0), anchor='w')

        self.image_size = tk.StringVar()
        self.image_size.set(f"Image capture size: {self.configuration.camera['image_width']}x{self.configuration.camera['image_height']}")
        self.preview_size_label = tk.Label(self.info_frame, textvariable=self.image_size, font=self.font)
        self.preview_size_label.pack(side=tk.TOP, padx=(5,0), pady=(5,0), anchor='w')

        self.ai_image_size = tk.StringVar()
        self.ai_image_size.set(f"AI detection size: {self.configuration.ai_detection['image_width']}x{self.configuration.ai_detection['image_height']}")
        self.ai_preview_size_label = tk.Label(self.info_frame, textvariable=self.ai_image_size, font=self.font)
        self.ai_preview_size_label.pack(side=tk.TOP, padx=(5,0), pady=(5,0), anchor='w')

        self.fps = tk.StringVar()
        self.fps.set('Preview FPS: ?')
        self.preview_fps_label = tk.Label(self.info_frame, textvariable=self.fps, font=self.font)
        self.preview_fps_label.pack(side=tk.TOP, padx=(5,0), pady=(5,0), anchor='w')

        self.cpu_temp_str = tk.StringVar()
        self.cpu_temp_str.set(f"CPU Temperature:  {rpi.get_temperature():.1f} \u00B0C (must be less than 80 \u00B0C)")
        self.cpu_temp_label = tk.Label(self.info_frame, textvariable=self.cpu_temp_str, font=self.font)
        self.cpu_temp_label.pack(side=tk.TOP, padx=(5,0), pady=(5,0), anchor='w')

        # Images
        crop_limits_frame = tk.Frame(notebook)
        crop_limits_frame.pack(side=tk.TOP, fill=tk.X, padx=(5,5), pady=(5,5), anchor='w')

        notebook.add(crop_limits_frame, text ='Images')

        crop_limits_subframe_1 = tk.Frame(crop_limits_frame)
        crop_limits_subframe_1.pack(side=tk.TOP, fill=tk.X)

        crop_limits_subframe_2 = tk.Frame(crop_limits_frame)
        crop_limits_subframe_2.pack(side=tk.TOP, fill=tk.X)

        crop_limits_subframe_3 = tk.Frame(crop_limits_frame)
        crop_limits_subframe_3.pack(side=tk.TOP, fill=tk.X, padx=(5,0))

        crop_limits_subframe_3_1 = tk.Frame(crop_limits_subframe_3)
        crop_limits_subframe_3_1.pack(side=tk.LEFT, fill=tk.X)

        crop_limits_subframe_3_2 = tk.Frame(crop_limits_subframe_3)
        crop_limits_subframe_3_2.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.crop_x_label = tk.Label(crop_limits_subframe_1, text='X', font=self.font)
        self.crop_x_label.pack(side=tk.LEFT, padx=(5,5))

        self.crop_x_entry = tk.Entry(crop_limits_subframe_1, width=TK_ENTRY_WIDTH, takefocus=False, font=self.font)
        self.crop_x_entry.insert(0, str(self.configuration.camera['sensor']['crop_limits'][0]))
        self.crop_x_entry.pack(side=tk.LEFT, padx=(5,5))

        self.crop_y_label = tk.Label(crop_limits_subframe_1, text='Y', font=self.font)
        self.crop_y_label.pack(side=tk.LEFT, padx=(5,5))

        self.crop_y_entry = tk.Entry(crop_limits_subframe_1, width=TK_ENTRY_WIDTH, takefocus=False, font=self.font)
        self.crop_y_entry.insert(0, str(self.configuration.camera['sensor']['crop_limits'][1]))
        self.crop_y_entry.pack(side=tk.LEFT, padx=(5,5))

        self.crop_width_label = tk.Label(crop_limits_subframe_1, text='Width:', font=self.font)
        self.crop_width_label.pack(side=tk.LEFT, padx=(5,5))

        self.crop_width_entry = tk.Entry(crop_limits_subframe_1, width=TK_ENTRY_WIDTH, takefocus=False, font=self.font)
        self.crop_width_entry.insert(0, str(self.configuration.camera['sensor']['crop_limits'][2]))
        self.crop_width_entry.pack(side=tk.LEFT, padx=(5,5))

        self.crop_height_label = tk.Label(crop_limits_subframe_1, text='Height', font=self.font)
        self.crop_height_label.pack(side=tk.LEFT, padx=(5,5))

        self.crop_height_entry = tk.Entry(crop_limits_subframe_1, width=TK_ENTRY_WIDTH, takefocus=False, font=self.font)
        self.crop_height_entry.insert(0, str(self.configuration.camera['sensor']['crop_limits'][3]))
        self.crop_height_entry.pack(side=tk.LEFT, padx=(5,5))

        self.crop_center_button = tk.Button(crop_limits_subframe_1, text='Center', takefocus=False, command=self.center_crop_limits, font=self.font)
        self.crop_center_button.pack(side=tk.LEFT, padx=(5,5), pady=(5,5))

        self.crop_center_button = tk.Button(crop_limits_subframe_1, text='Full size', takefocus=False, command=self.set_full_size_crop_limits, font=self.font)
        self.crop_center_button.pack(side=tk.LEFT, padx=(0,5), pady=(5,5))

        self.crop_save_button = tk.Button(crop_limits_subframe_1, text='Save', takefocus=False, command=self.save_crop_limits, font=self.font)
        self.crop_save_button.pack(side=tk.RIGHT, padx=(0,5), pady=(5,5))

        crop_limits_subframe_3_1.rowconfigure(0, weight=1)
        crop_limits_subframe_3_1.rowconfigure(1, weight=1)
        crop_limits_subframe_3_1.rowconfigure(2, weight=1)

        crop_limits_subframe_3_1.columnconfigure(0, weight=1)
        crop_limits_subframe_3_1.columnconfigure(1, weight=1)
        crop_limits_subframe_3_1.columnconfigure(2, weight=1)

        self.crop_limits_go_up = tk.Button(crop_limits_subframe_3_1, text='\u2B06', command=partial(self.move_crop_limits, 'up'), takefocus=False, font=self.font_arrows)
        self.crop_limits_go_up.grid(row=0, column=1)

        self.crop_limits_go_left = tk.Button(crop_limits_subframe_3_1, text='\u2B05', command=partial(self.move_crop_limits, 'left'), takefocus=False, font=self.font_arrows)
        self.crop_limits_go_left.grid(row=1, column=0)

        self.crop_limits_entry = tk.Entry(crop_limits_subframe_3_1, width=TK_ENTRY_WIDTH, takefocus=False, font=self.font)
        self.crop_limits_entry.insert(0, '10')
        self.crop_limits_entry.grid(row=1, column=1)

        self.crop_limits_go_right = tk.Button(crop_limits_subframe_3_1, text='\u27A1', command=partial(self.move_crop_limits, 'right'), takefocus=False, font=self.font_arrows)
        self.crop_limits_go_right.grid(row=1, column=3)

        self.crop_limits_go_down = tk.Button(crop_limits_subframe_3_1, text='\u2B07', command=partial(self.move_crop_limits, 'down'), takefocus=False, font=self.font_arrows)
        self.crop_limits_go_down.grid(row=2, column=1)

        button = tk.Button(crop_limits_subframe_3_2, text='Capture image', takefocus=False, command=self.save_image, font=self.font)
        button.pack(side=tk.LEFT, expand=True)

        button = tk.Button(crop_limits_subframe_3_2, text='Capture image + flash', takefocus=False, command=self.save_image_flash, font=self.font)
        button.pack(side=tk.LEFT, expand=True)
        
        # AI Detection
        self.ai_frame = tk.Frame(notebook)
        self.ai_frame.pack(side=tk.TOP, fill=tk.X, padx=(5,5), pady=(5,5), anchor='w')

        notebook.add(self.ai_frame, text ='AI Detection')

        ai_subframe_1 = tk.Frame(self.ai_frame)
        ai_subframe_1.pack(side=tk.TOP, fill=tk.X)

        ai_subframe_2 = tk.Frame(self.ai_frame)
        ai_subframe_2.pack(side=tk.TOP, fill=tk.X)

        ai_subframe_3 = tk.Frame(self.ai_frame)
        ai_subframe_3.pack(side=tk.TOP, fill=tk.X)

        ai_subframe_4 = tk.Frame(self.ai_frame)
        ai_subframe_4.pack(side=tk.TOP, fill=tk.X)

        self.ai_enable = tk.IntVar()
        self.ai_enable.set(self.configuration.ai_detection['enable'])
        self.ai_enable_radiobutton = tk.Checkbutton(ai_subframe_1, text='Enable', variable=self.ai_enable, onvalue=1, offvalue=0, takefocus=False, font=self.font)
        self.ai_enable_radiobutton.pack(side=tk.LEFT, padx=(5,0))

        self.ai_enable_set_button = tk.Button(ai_subframe_1, text='Save', takefocus=False, command=self.save_ai_enable, font=self.font)
        self.ai_enable_set_button.pack(side=tk.RIGHT, padx=(0,5), pady=(5,5))

        self.ai_min_conf_label = tk.Label(ai_subframe_2, text='Min. confidence:', font=self.font)
        self.ai_min_conf_label.pack(side=tk.LEFT, padx=(5,5))

        self.ai_min_conf_entry = tk.Entry(ai_subframe_2, width=TK_ENTRY_WIDTH, takefocus=False, font=self.font)
        self.ai_min_conf_entry.insert(0, str(self.configuration.ai_detection['min_confidence']))
        self.ai_min_conf_entry.pack(side=tk.LEFT, padx=(5,5))

        self.ai_min_conf_set_button = tk.Button(ai_subframe_2, text='Save', takefocus=False, command=self.save_ai_min_conf, font=self.font)
        self.ai_min_conf_set_button.pack(side=tk.RIGHT, padx=(0,5), pady=(0,5))

        self.ai_preview_size_label = tk.Label(ai_subframe_3, text='Detection image scale (%):', font=self.font)
        self.ai_preview_size_label.pack(side=tk.LEFT, padx=(5,5))

        self.ai_image_scale_entry = tk.Entry(ai_subframe_3, width=TK_ENTRY_WIDTH, takefocus=False, font=self.font)
        self.ai_image_scale_entry.insert(0, f"{100*self.configuration.ai_detection['image_width']/self.configuration.camera['image_width']:.2f}")
        self.ai_image_scale_entry.pack(side=tk.LEFT, padx=(5,5))

        self.ai_image_size_2 = tk.StringVar()
        self.ai_image_size_2.set(f"=> Detection image size: {self.configuration.ai_detection['image_width']}x{self.configuration.ai_detection['image_height']}")
        self.ai_image_size_2_label = tk.Label(ai_subframe_3, textvariable=self.ai_image_size_2, font=self.font)
        self.ai_image_size_2_label.pack(side=tk.LEFT, padx=(5,5))

        self.ai_image_size_set_button = tk.Button(ai_subframe_3, text='Save', takefocus=False, command=self.save_ai_image_size, font=self.font)
        self.ai_image_size_set_button.pack(side=tk.RIGHT, padx=(0,5), pady=(0,5))

        self.ai_speed = tk.IntVar()
        self.ai_speed.set('Speed: 0 ms')
        self.ai_speed_label = tk.Label(ai_subframe_4, textvariable=self.ai_speed, font=self.font)
        self.ai_speed_label.pack(side=tk.LEFT, padx=(5,0))

        self.save_ai_capture = tk.IntVar()
        self.save_ai_capture.set(False)
        self.save_ai_capture_radiobutton = tk.Checkbutton(ai_subframe_4, text='Save AI capture', variable=self.save_ai_capture, onvalue=1, offvalue=0, takefocus=False, font=self.font)
        self.save_ai_capture_radiobutton.pack(side=tk.LEFT, padx=(5,0))

        # LEDs
        self.leds_frame = tk.Frame(notebook)
        self.leds_frame.pack(side=tk.TOP, fill=tk.X, padx=(5,5), pady=(5,5), anchor='w')

        notebook.add(self.leds_frame, text ='LEDs')

        leds_subframe_1 = tk.Frame(self.leds_frame)
        leds_subframe_1.pack(side=tk.TOP, fill=tk.X)

        leds_subframe_2 = tk.Frame(self.leds_frame)
        leds_subframe_2.pack(side=tk.TOP, fill=tk.X)

        leds_subframe_3 = tk.Frame(self.leds_frame)
        leds_subframe_3.pack(side=tk.TOP, fill=tk.X)

        capture_images_mode_label = tk.Label(leds_subframe_1, text='Mode:', font=self.font)
        capture_images_mode_label.pack(side=tk.LEFT, padx=(5,0))

        self.images_capture_mode_combobox = ttk.Combobox(leds_subframe_1, values=['Trap', 'Lepinoc', 'Deported'], state='readonly', width=TK_COMBOBOX_WIDTH, takefocus=False, font=self.font)
        self.images_capture_mode_combobox.pack(side=tk.LEFT, padx=(0,5), pady=(0,5))
        self.images_capture_mode_combobox.current(self.configuration.leds['mode'] - 1)
        self.images_capture_mode_combobox.bind('<<ComboboxSelected>>', self.set_images_capture_mode)

        self.images_capture_mode_set_button = tk.Button(leds_subframe_1, text='Save', command=self.save_images_capture_mode, takefocus=False, font=self.font)
        self.images_capture_mode_set_button.pack(side=tk.RIGHT, padx=(0,5), pady=(5,5))

        self.leds_front_scale = tk.Scale(leds_subframe_2, from_=0, to=100, orient=tk.HORIZONTAL, length=TK_SCALE_WIDTH, resolution=1, label='LEDs front', takefocus=False, font=self.font)
        self.leds_front_scale.set(self.configuration.leds['intensity_front'])
        self.leds_front_scale_binding = self.leds_front_scale.bind('<ButtonRelease-1>', lambda event, leds='front' : self.set_leds_intensity(leds))
        self.leds_front_scale.pack(side=tk.LEFT, padx=(5,0), pady=(0,5))

        self.leds_rear_scale = tk.Scale(leds_subframe_2, from_=0, to=100, orient=tk.HORIZONTAL, length=TK_SCALE_WIDTH, resolution=1, label='LEDs rear', takefocus=False, font=self.font)
        self.leds_rear_scale.set(self.configuration.leds['intensity_rear'])
        self.leds_rear_scale_binding = self.leds_rear_scale.bind('<ButtonRelease-1>', lambda event, leds='rear' : self.set_leds_intensity(leds))
        self.leds_rear_scale.pack(side=tk.LEFT, padx=(5,0), pady=(0,5))

        self.leds_deported_scale = tk.Scale(leds_subframe_2, from_=0, to=100, orient=tk.HORIZONTAL, length=TK_SCALE_WIDTH, resolution=1, label='LEDS deported', takefocus=False, font=self.font)
        self.leds_deported_scale.set(self.configuration.leds['intensity_deported'])
        self.leds_deported_scale_binding = self.leds_deported_scale.bind('<ButtonRelease-1>', lambda event, leds='deported' : self.set_leds_intensity(leds))
        self.leds_deported_scale.pack(side=tk.LEFT, padx=(5,0), pady=(0,5))

        self.leds_uv_scale = tk.Scale(leds_subframe_2, from_=0, to=100, orient=tk.HORIZONTAL, length=TK_SCALE_WIDTH, resolution=1, label='LEDs UV', takefocus=False, font=self.font)
        self.leds_uv_scale.set(self.configuration.leds['intensity_uv'])
        self.leds_uv_scale_binding = self.leds_uv_scale.bind('<ButtonRelease-1>', lambda event, leds='uv' : self.set_leds_intensity(leds))
        self.leds_uv_scale.pack(side=tk.LEFT, padx=(5,0), pady=(0,5))

        self.leds_save_button = tk.Button(leds_subframe_2, text='Save', command=self.save_leds_intensity, takefocus=False, font=self.font)
        self.leds_save_button.pack(side=tk.RIGHT, padx=(0,5), pady=(5,0))

        mode = self.configuration.leds['mode']

        if mode == 1:

            self.leds_rear_scale.pack(side=tk.LEFT, padx=(5,0), pady=(0,5))
            self.leds_front_scale.pack(side=tk.LEFT, padx=(5,0), pady=(0,5))
            self.leds_deported_scale.pack_forget()
            self.leds_uv_scale.pack_forget()

            self.set_leds_intensity('rear')
            self.set_leds_intensity('front')

        elif mode == 2:

            self.leds_rear_scale.pack_forget()
            self.leds_front_scale.pack(side=tk.LEFT, padx=(5,0), pady=(0,5))
            self.leds_deported_scale.pack_forget()
            self.leds_uv_scale.pack(side=tk.LEFT, padx=(5,0), pady=(0,5))

            self.set_leds_intensity('front')
            self.set_leds_intensity('uv')

        elif mode == 3:

            self.leds_rear_scale.pack_forget()
            self.leds_front_scale.pack_forget()
            self.leds_deported_scale.pack(side=tk.LEFT, padx=(5,0), pady=(0,5))
            self.leds_uv_scale.pack_forget()

            self.set_leds_intensity('deported')
            
        self.leds_delay_label = tk.Label(leds_subframe_3, text='Delay after on (s):', font=self.font)
        self.leds_delay_label.pack(side=tk.LEFT, padx=(5,5))

        self.leds_delay_on_entry = tk.Entry(leds_subframe_3, width=TK_ENTRY_WIDTH, takefocus=False, font=self.font)
        self.leds_delay_on_entry.insert(0, str(self.configuration.leds['delay_on']))
        self.leds_delay_on_entry.pack(side=tk.LEFT, padx=(5,5))

        self.leds_delay_label = tk.Label(leds_subframe_3, text='Delay before off (s):', font=self.font)
        self.leds_delay_label.pack(side=tk.LEFT, padx=(5,5))

        self.leds_delay_off_entry = tk.Entry(leds_subframe_3, width=TK_ENTRY_WIDTH, takefocus=False, font=self.font)
        self.leds_delay_off_entry.insert(0, str(self.configuration.leds['delay_off']))
        self.leds_delay_off_entry.pack(side=tk.LEFT, padx=(5,5))
        
        self.leds_delay_save_button = tk.Button(leds_subframe_3, text='Save', command=self.save_leds_delay, takefocus=False, font=self.font)
        self.leds_delay_save_button.pack(side=tk.RIGHT, padx=(0,5), pady=(5,0))
        
        # Image adjustments
        image_adjustments_frame = tk.Frame(notebook)
        image_adjustments_frame.pack(side=tk.TOP, fill=tk.X, padx=(5,5), pady=(5,5), anchor='w')

        notebook.add(image_adjustments_frame, text ='Image adjustments')

        image_adjustments_frame_subframe_1 = tk.Frame(image_adjustments_frame)
        image_adjustments_frame_subframe_1.pack(side=tk.LEFT, fill=tk.Y)

        image_adjustments_frame_subframe_2 = tk.Frame(image_adjustments_frame)
        image_adjustments_frame_subframe_2.pack(side=tk.LEFT, fill=tk.Y)

        image_adjustments_frame_subframe_3 = tk.Frame(image_adjustments_frame)
        image_adjustments_frame_subframe_3.pack(side=tk.RIGHT, fill=tk.Y)

        self.brightness_scale = tk.Scale(image_adjustments_frame_subframe_1, from_=-1.0, to=1.0, orient=tk.HORIZONTAL, length=TK_SCALE_WIDTH, resolution=0.05, label='Brightness', takefocus=False, font=self.font)
        self.brightness_scale.set(value=self.configuration.camera['image_adjustments']['brightness'])
        self.brightness_scale.bind('<ButtonRelease-1>', lambda event, ctrl='brightness' : self.set_image_adjustments(ctrl))
        self.brightness_scale.pack(side=tk.TOP, padx=(5,0), pady=(0,5))

        self.sharpness_scale = tk.Scale(image_adjustments_frame_subframe_1, from_=0.0, to=16.0, orient=tk.HORIZONTAL, length=TK_SCALE_WIDTH, resolution=0.05, label='Sharpness', takefocus=False, font=self.font)
        self.sharpness_scale.set(value=self.configuration.camera['image_adjustments']['sharpness'])
        self.sharpness_scale.bind('<ButtonRelease-1>', lambda event, ctrl='sharpness' : self.set_image_adjustments(ctrl))
        self.sharpness_scale.pack(side=tk.TOP, padx=(5,0), pady=(0,5))

        self.contrast_scale = tk.Scale(image_adjustments_frame_subframe_2, from_=0.0, to=32.0, orient=tk.HORIZONTAL, length=TK_SCALE_WIDTH, resolution=0.05, label='Contrast', takefocus=False, font=self.font)
        self.contrast_scale.set(value=self.configuration.camera['image_adjustments']['contrast'])
        self.contrast_scale.bind('<ButtonRelease-1>', lambda event, ctrl='contrast' : self.set_image_adjustments(ctrl))
        self.contrast_scale.pack(side=tk.TOP, padx=(5,0), pady=(0,5))

        self.saturation_scale = tk.Scale(image_adjustments_frame_subframe_2, from_=0.0, to=32.0, orient=tk.HORIZONTAL, length=TK_SCALE_WIDTH, resolution=0.05, label='Saturation', takefocus=False, font=self.font)
        self.saturation_scale.set(value=self.configuration.camera['image_adjustments']['saturation'])
        self.saturation_scale.bind('<ButtonRelease-1>', lambda event, ctrl='saturation' : self.set_image_adjustments(ctrl))
        self.saturation_scale.pack(side=tk.TOP, padx=(5,0), pady=(0,5))

        self.image_adjustments_save_button = tk.Button(image_adjustments_frame_subframe_3, text='Save', command=self.save_image_adjustments, takefocus=False, font=self.font)
        self.image_adjustments_save_button.pack(side=tk.TOP, padx=(0,5), pady=(5,0))

        # White Balance
        awb_frame = tk.Frame(notebook)
        awb_frame.pack(side=tk.TOP, fill=tk.X, padx=(5,5), pady=(5,5), anchor='w')

        notebook.add(awb_frame, text ='White Balance')

        subframe = tk.Frame(awb_frame)
        subframe.pack(side=tk.TOP, fill=tk.X)

        self.awb_mode = tk.StringVar()
        self.awb_combobox = ttk.Combobox(subframe, state='readonly', textvariable=self.awb_mode, values = ['Auto', 'Tungsten', 'Fluorescent', 'Indoor', 'Daylight', 'Cloudy'], width=TK_COMBOBOX_WIDTH, takefocus=False, font=self.font)
        self.awb_mode.set(self.configuration.camera['white_balance']['mode'])
        self.awb_combobox.bind('<<ComboboxSelected>>', self.set_awb_mode)
        self.awb_combobox.pack(side=tk.LEFT, padx=(5,0), pady=(5,0))

        self.awb_save_button = tk.Button(subframe, text='Save', command=self.save_awb_mode, takefocus=False, font=self.font)
        self.awb_save_button.pack(side=tk.RIGHT, padx=(0,5), pady=(5,0))

        # Autofocus
        if self.camera.available and self.camera.autofocus_available:

            auto_focus_frame = tk.Frame(notebook)
            auto_focus_frame.pack(side=tk.TOP, fill=tk.X, padx=(5,5), pady=(5,5), anchor='w')

            notebook.add(auto_focus_frame, text ='Autofocus')

            auto_focus_subframe_1 = tk.Frame(auto_focus_frame)
            auto_focus_subframe_1.pack(side=tk.TOP, fill=tk.X)

            self.auto_focus_subframe_2 = tk.Frame(auto_focus_frame)

            self.auto_focus_subframe_3 = tk.Frame(auto_focus_frame)

            self.auto_focus_subframe_4 = tk.Frame(auto_focus_frame)

            label = tk.Label(auto_focus_subframe_1, text='Mode:', font=self.font)
            label.pack(side=tk.LEFT, padx=(5,0))

            self.af_mode = tk.StringVar()
            if self.configuration.camera['autofocus']['mode'] == 'Manual':
                self.af_mode.set('M')
                self.auto_focus_subframe_4.pack(side=tk.TOP, fill=tk.X)
            # elif self.configuration.camera['autofocus']['mode'] == 'Auto':
                # self.af_mode.set('A')
            elif self.configuration.camera['autofocus']['mode'] == 'Continuous':
                self.af_mode.set('C')
                self.auto_focus_subframe_2.pack(side=tk.TOP, fill=tk.X)
                self.auto_focus_subframe_3.pack(side=tk.TOP, fill=tk.X)

            self.af_manual_radiobutton = tk.Radiobutton(auto_focus_subframe_1, text="Manual", variable=self.af_mode, value='M', command=self.select_af_mode, takefocus=False, font=self.font)
            self.af_manual_radiobutton.pack(side=tk.LEFT)
            # self.af_auto_radiobutton = tk.Radiobutton(auto_focus_mode_label_frame, text="Auto", variable=self.af_mode, value='A', command=self.select_af_mode, font=self.font)
            # self.af_auto_radiobutton.pack(side=tk.LEFT)
            self.af_continuous_radiobutton = tk.Radiobutton(auto_focus_subframe_1, text="Continuous", variable=self.af_mode, value='C', command=self.select_af_mode, takefocus=False, font=self.font)
            self.af_continuous_radiobutton.pack(side=tk.LEFT)


            label = tk.Label(self.auto_focus_subframe_2, text='Range:', font=self.font)
            label.pack(side=tk.LEFT, padx=(5,0))

            self.af_range = tk.StringVar()
            if self.configuration.camera['autofocus']['range'] == 'Normal':
                self.af_range.set('N')
            elif self.configuration.camera['autofocus']['range'] == 'Macro':
                self.af_range.set('M')
            elif self.configuration.camera['autofocus']['range'] == 'Full':
                self.af_range.set('F')
            self.af_range_normal_radiobutton = tk.Radiobutton(self.auto_focus_subframe_2, text='Normal', variable=self.af_range, value='N', command=self.select_af_mode, takefocus=False, font=self.font)
            self.af_range_normal_radiobutton.pack(side=tk.LEFT)
            self.af_range_macro_radiobutton = tk.Radiobutton(self.auto_focus_subframe_2, text='Macro', variable=self.af_range, value='M', command=self.select_af_mode, takefocus=False, font=self.font)
            self.af_range_macro_radiobutton.pack(side=tk.LEFT)
            self.af_range_full_radiobutton = tk.Radiobutton(self.auto_focus_subframe_2, text='Full', variable=self.af_range, value='F', command=self.select_af_mode, takefocus=False, font=self.font)
            self.af_range_full_radiobutton.pack(side=tk.LEFT)

            label = tk.Label(self.auto_focus_subframe_3, text='Speed:', font=self.font)
            label.pack(side=tk.LEFT, padx=(5,0))

            self.af_speed = tk.StringVar()
            self.af_speed.set('N')
            if self.configuration.camera['autofocus']['speed'] == 'Normal':
                self.af_speed.set('N')
            elif self.configuration.camera['autofocus']['speed'] == 'Fast':
                self.af_speed.set('F')
            self.af_speed_normal_radiobutton = tk.Radiobutton(self.auto_focus_subframe_3, text='Normal', variable=self.af_speed, value='N', command=self.select_af_mode, takefocus=False, font=self.font)
            self.af_speed_normal_radiobutton.pack(side=tk.LEFT)
            self.af_speed_fast_radiobutton = tk.Radiobutton(self.auto_focus_subframe_3, text='Fast', variable=self.af_speed, value='F', command=self.select_af_mode, takefocus=False, font=self.font)
            self.af_speed_fast_radiobutton.pack(side=tk.LEFT)

            lens_position = self.configuration.camera['autofocus']['lens_position']

            label = tk.Label(self.auto_focus_subframe_4, text='Lens Position:', font=self.font)
            label.pack(side=tk.LEFT, padx=(5,0))
            self.lens_position_scale = tk.Scale(self.auto_focus_subframe_4, from_=0.0, to=32.0, orient=tk.HORIZONTAL, length=TK_SCALE_WIDTH, resolution=0.1, takefocus=False, font=self.font)
            self.lens_position_scale.set(value=lens_position)
            self.lens_position_scale.bind('<ButtonRelease-1>', self.select_lens_position)
            self.lens_position_scale.pack(side=tk.LEFT)

            self.lens_distance = tk.StringVar()
            self.lens_distance.set(f'(distance \u2243 {100/lens_position:.1f} cm)')

            label = tk.Label(self.auto_focus_subframe_4, textvariable=self.lens_distance, font=self.font)
            label.pack(side=tk.LEFT, padx=(5,0))

            self.af_save_button = tk.Button(auto_focus_subframe_1, text='Save', command=self.save_af, takefocus=False, font=self.font)
            self.af_save_button.pack(side=tk.RIGHT, padx=(0,5), pady=(5,0))

        # Auto Exposure/Gain
        auto_exposure_gain_frame = tk.Frame(notebook)
        auto_exposure_gain_frame.pack(side=tk.TOP, fill=tk.X, padx=(5,5), pady=(5,5), anchor='w')

        notebook.add(auto_exposure_gain_frame, text ='Exposure/Gain')

        exposure_gain_subframe_1 = tk.Frame(auto_exposure_gain_frame)
        exposure_gain_subframe_1.pack(side=tk.TOP, fill=tk.X)

        self.exposure_gain_subframe_2 = tk.Frame(auto_exposure_gain_frame)

        self.exposure_gain_subframe_3 = tk.Frame(auto_exposure_gain_frame)

        self.exposure_gain_subframe_4 = tk.Frame(auto_exposure_gain_frame)

        self.exposure_gain_subframe_5 = tk.Frame(auto_exposure_gain_frame)

        label = tk.Label(exposure_gain_subframe_1, text='Mode:', font=self.font)
        label.pack(side=tk.LEFT, padx=(5,0))

        self.auto_exposure_gain_enable = tk.StringVar()
        if self.configuration.camera['exposure_gain']['mode'] == 'Auto':
            self.auto_exposure_gain_enable.set('A')
            self.exposure_gain_subframe_5.pack(side=tk.TOP, fill=tk.X)
        else:
            self.auto_exposure_gain_enable.set('M')
            self.exposure_gain_subframe_2.pack(side=tk.TOP, fill=tk.X)
            self.exposure_gain_subframe_3.pack(side=tk.TOP, fill=tk.X)
            self.exposure_gain_subframe_4.pack(side=tk.TOP, fill=tk.X)

        self.manual_exposure_gain_radiobutton = tk.Radiobutton(exposure_gain_subframe_1, text='Manual', variable=self.auto_exposure_gain_enable, value='M', command=self.select_aeg_mode, takefocus=False, font=self.font)
        self.manual_exposure_gain_radiobutton.pack(side=tk.LEFT)

        self.auto_exposure_gain_radiobutton = tk.Radiobutton(exposure_gain_subframe_1, text='Auto', variable=self.auto_exposure_gain_enable, value='A', command=self.select_aeg_mode, takefocus=False, font=self.font)
        self.auto_exposure_gain_radiobutton.pack(side=tk.LEFT)

        self.exposure_mode = tk.StringVar()

        if self.configuration.camera['exposure_gain']['exposure_mode'] == 'Normal':
            self.exposure_mode.set('N')
        elif self.configuration.camera['exposure_gain']['exposure_mode'] == 'Short':
            self.exposure_mode.set('S')
        elif self.configuration.camera['exposure_gain']['exposure_mode'] == 'Long':
            self.exposure_mode.set('L')

        self.exposure_normal_radiobutton = tk.Radiobutton(self.exposure_gain_subframe_5, text='Normal', variable=self.exposure_mode, value='N', command= lambda event=None : self.set_aeg_mode(event), takefocus=False, font=self.font)
        self.exposure_normal_radiobutton.pack(side=tk.LEFT)
        self.exposure_short_radiobutton = tk.Radiobutton(self.exposure_gain_subframe_5, text='Short', variable=self.exposure_mode, value='S', command= lambda event=None : self.set_aeg_mode(event), takefocus=False, font=self.font)
        self.exposure_short_radiobutton.pack(side=tk.LEFT)
        self.exposure_long_radiobutton = tk.Radiobutton(self.exposure_gain_subframe_5, text='Long', variable=self.exposure_mode, value='L', command= lambda event=None : self.set_aeg_mode(event), takefocus=False, font=self.font)
        self.exposure_long_radiobutton.pack(side=tk.LEFT)
        # self.exposure_custom_radiobutton = Radiobutton(auto_exposure_gain_frame, text="Custom", variable=self.af_mode, value='C', command=self.select_af_mode)
        # self.exposure_custom_radiobutton.grid(row=0, column=4)

        label = tk.Label(self.exposure_gain_subframe_2, text='Analog Gain:', font=self.font)
        label.pack(side=tk.LEFT, padx=(5,0))

        self.analog_gain_scale = tk.Scale(self.exposure_gain_subframe_2, from_=0.0, to=20.0, orient=tk.HORIZONTAL, length=TK_SCALE_WIDTH, resolution=0.1, takefocus=False, font=self.font)
        self.analog_gain_scale.set(self.configuration.camera['exposure_gain']['analog_gain'])
        self.analog_gain_scale.bind('<ButtonRelease-1>', self.set_aeg_mode)
        self.analog_gain_scale.pack(side=tk.LEFT, padx=(5,0), pady=(0,0))

        label = tk.Label(self.exposure_gain_subframe_3, text='Exposure Time (\u03BCs):', font=self.font)
        label.pack(side=tk.LEFT, padx=(5,0))

        self.exposure_time_scale = tk.Scale(self.exposure_gain_subframe_3, from_=0, to=EXPOSURE_TIME_MAX, orient=tk.HORIZONTAL, length=TK_SCALE_WIDTH, resolution=1, takefocus=False, font=self.font)
        self.exposure_time_scale.set(self.configuration.camera['exposure_gain']['exposure_time'])
        self.exposure_time_scale.bind('<ButtonRelease-1>', self.set_aeg_mode)
        self.exposure_time_scale.pack(side=tk.LEFT, padx=(5,0), pady=(0,0))

        label = tk.Label(self.exposure_gain_subframe_4, text='Exposure Value:', font=self.font)
        label.pack(side=tk.LEFT, padx=(5,0))

        self.exposure_value_scale = tk.Scale(self.exposure_gain_subframe_4, from_=-8.0, to=8.0, orient=tk.HORIZONTAL, length=TK_SCALE_WIDTH, resolution=0.1, takefocus=False, font=self.font)
        self.exposure_value_scale.set(self.configuration.camera['exposure_gain']['exposure_value'])
        self.exposure_value_scale.bind('<ButtonRelease-1>', self.set_aeg_mode)
        self.exposure_value_scale.pack(side=tk.LEFT, padx=(5,0), pady=(0,0))

        self.auto_exposure_gain_save_button = tk.Button(exposure_gain_subframe_1, text='Save', takefocus=False, command=self.save_aeg_mode, font=self.font)
        self.auto_exposure_gain_save_button.pack(side=tk.RIGHT, padx=(0,5), pady=(5,0))

        # Fan
        # fan_frame = tk.Frame(notebook)
        # fan_frame.pack(side=tk.TOP, fill=tk.X, padx=(5,5), pady=(5,5))
        
        # notebook.add(fan_frame, text ='Fan')
        
        # Files
        files_frame = tk.Frame(notebook)
        files_frame.pack(side=tk.TOP, fill=tk.X, padx=(5,5), pady=(5,5))

        files_subframe_1 = tk.Frame(files_frame)
        files_subframe_1.pack(side=tk.TOP, fill=tk.X, anchor='w')

        self.images_capture_jpeg_label = tk.Label(files_subframe_1, text='JPEG quality (%): ', font=self.font)
        self.images_capture_jpeg_label.pack(side=tk.LEFT, padx=(5,5))

        self.images_capture_jpeg_entry = tk.Entry(files_subframe_1, width=TK_ENTRY_WIDTH, takefocus=False, font=self.font)
        self.images_capture_jpeg_entry.insert(0, str(self.configuration.files['jpeg_quality']))
        self.images_capture_jpeg_entry.pack(side=tk.LEFT, padx=(5,5))

        self.images_capture_jpeg_set_button = tk.Button(files_subframe_1, text='Save', takefocus=False, command=self.save_images_capture_jpeg_quality, font=self.font)
        self.images_capture_jpeg_set_button.pack(side=tk.RIGHT, padx=(0,5), pady=(5,5))

        notebook.add(files_frame, text ='Files')

        # # Sensor modes
        # sensor_modes_frame = tk.Frame(notebook)
        # sensor_modes_frame.pack(side=tk.TOP, fill=tk.X, padx=(5,5), pady=(5,5))

        # notebook.add(sensor_modes_frame, text ='Sensor Modes')

        # values = []
        # for i in range(0, len(self.camera.camera.sensor_modes)):
            # values.append(f'Mode {i}')

        # self.sensor_modes_combobox = ttk.Combobox(sensor_modes_frame, values=values, state="readonly", width=TK_COMBOBOX_WIDTH, font=self.font)
        # self.sensor_modes_combobox.pack(side=tk.TOP, padx=(5,5), pady=(5,5), anchor='w')
        # self.sensor_modes_combobox.current(self.configuration.camera['sensor']['mode'])
        # # self.sensor_modes_combobox.bind('<<ComboboxSelected>>', self.set_images_capture_mode)

        notebook.pack(expand=True, fill=tk.BOTH, padx=(5,5), pady=(0,5))

    def save_image(self):

        self.take_photo = True

    def save_image_flash(self):

        self.take_photo_flash = True
        
    def update_configuration_display(self):

        configuration = self.configuration.to_string()

        s = configuration.find('Laser\n')
        e = configuration.find('Leds\n')

        configuration = configuration[:s] + configuration[e:]

        s = configuration.find('Gnss\n')
        e = configuration.find('Leds\n')

        configuration = configuration[:s] + configuration[e:]

        s = configuration.find('Monitor environment\n')
        configuration = configuration[:s]

        self.configuration_scolltext.configure(state=tk.NORMAL)
        self.configuration_scolltext.delete('0.0', tk.END)
        self.configuration_scolltext.insert(tk.END, configuration)
        self.configuration_scolltext.configure(state=tk.DISABLED)

    def image_click(self, event):

        pass

        # x = self.preview_canvas.canvasx(event.x)
        # y = self.preview_canvas.canvasy(event.y)

        # # print(x)
        # # print(y)

        # # x = TK_IMAGE_WIDTH_MAX//2
        # # y = TK_IMAGE_HEIGHT_MAX//2

        # # x = 0
        # # y = 0

        # if event.num == 1:

            # self.preview_scale *= 2

            # self.preview_canvas.scale('all', x, y, self.preview_scale, self.preview_scale)

            # # self.camera_setup_label_frame.forget()
            # # self.ai_frame.forget()
            # # self.leds_frame.forget()
            # # # self.preview_info_label_frame.forget()
            # # self.preview_info_label_frame.pack(side=tk.TOP, expand=True, fill=tk.BOTH, padx=(5,5), pady=(0,5))

        # elif event.num == 3:

            # self.preview_scale /= 2

            # self.preview_canvas.scale('all', x, y, self.preview_scale, self.preview_scale)
            # # self.camera_setup_label_frame.pack(side=tk.TOP, fill=tk.X)
            # # self.ai_frame.pack(side=tk.TOP, fill=tk.X, padx=(5,5), pady=(5,5), anchor='w')
            # # self.leds_frame.pack(side=tk.TOP, fill=tk.X, padx=(5,5), pady=(5,5), anchor='w')
            # # self.preview_info_label_frame.pack(side=tk.TOP, expand=False, fill=tk.BOTH, padx=(5,5), pady=(0,5))

        # print(self.preview_scale)

        # # print(event.num)
        # # print(event.x)
        # # print(event.y)

    def save_ai_enable(self):

        if self.ai_enable.get():
            self.configuration.ai_detection['enable'] = True
        else:
            self.configuration.ai_detection['enable'] = False

        self.configuration.save()

        self.configuration.read()

        self.update_configuration_display()

        if self.ai_enable.get():
            self.status_text.set('New configuration saved: AI detection enabled')
            logger.info(f'{this_script}: AI detection enabled')
        else:
            self.status_text.set('New configuration saved: AI detection disabled')
            logger.info(f'{this_script}: AI detection disabled')

    def save_ai_min_conf(self):

        min_conf = self.ai_min_conf_entry.get()

        try:

            min_conf = float(min_conf)

            if min_conf > 0 and min_conf < 1.0:

                self.configuration.ai_detection['min_confidence'] = min_conf

                self.configuration.save()

                self.configuration.read()

                self.update_configuration_display()

                self.status_text.set(f'New configuration saved: AI minimal confidence set to {min_conf}')
                logger.info(f'{this_script}: AI minimal confidence set to {min_conf}')

            else:

                self.ai_min_conf_entry.delete('0', tk.END)
                self.ai_min_conf_entry.insert(tk.END, self.configuration.ai_detection['min_confidence'])
                self.status_text.set('Error: AI minimal confidence must be a positive float number in the range ]0.0 1.0[')
                logger.error(f'{this_script}: AI minimal confidence must be a positive float number in the range ]0.0 1.0[')

        except BaseException as e:

            self.ai_min_conf_entry.delete('0', tk.END)
            self.ai_min_conf_entry.insert(tk.END, self.configuration.ai_detection['min_confidence'])
            self.status_text.set('Error: AI minimal confidence must be a positive float number in the range ]0.0 1.0[')

            logger.error(f'{this_script}: AI minimal confidence must be a positive float number in the range ]0.0 1.0[')
            logger.error(f'{this_script}: ' + str(e))

    def save_ai_image_size(self, update_camera_configuration=True):

        ai_image_scale = self.ai_image_scale_entry.get()

        try:

            ai_image_scale = float(ai_image_scale)

            if ai_image_scale > 0.0 and ai_image_scale <= 100.0:

                image_width = self.configuration.camera['image_width']
                ai_image_width = int(image_width * ai_image_scale / 100)
                # Multiple of 32 for AI but multiple of 64 for lores with YUV420 format
                # See "Appendix A: Pixel and image formats" in the Picamera2 library documentation
                # ai_image_width = ((ai_image_width // 32) + 1) * 32
                ai_image_width = ((ai_image_width // 64) + 1) * 64

                image_height = self.configuration.camera['image_height']
                ai_image_height = int(image_height * ai_image_scale / 100)
                # Multiple of 32 for AI but multiple of 64 for lores with YUV420 format
                # See "Appendix A: Pixel and image formats" in the Picamera2 library documentation
                # ai_image_height = ((ai_image_height // 32) + 1) * 32
                ai_image_height = ((ai_image_height // 64) + 1) * 64

                self.configuration.ai_detection['image_width'] = ai_image_width
                self.configuration.ai_detection['image_height'] = ai_image_height

                self.ai_image_size_2.set(f"=> Detection image size: {self.configuration.ai_detection['image_width']}x{self.configuration.ai_detection['image_height']}")
                self.ai_image_size.set(f"AI detection size: {self.configuration.ai_detection['image_width']}x{self.configuration.ai_detection['image_height']}")

                self.configuration.save()

                self.configuration.read()

                self.update_configuration_display()

                self.status_text.set(f'New configuration saved: AI image scale set to {ai_image_scale} %')
                logger.info(f'{this_script}: AI image scale set to {ai_image_scale} %')

                if update_camera_configuration:

                    self.camera.configure(self.configuration)

            else:

                ai_image_scale = 100 * self.configuration.ai_detection['image_width'] // self.configuration.camera['image_width']
                self.ai_image_scale_entry.delete('0', tk.END)
                self.ai_image_scale_entry.insert(tk.END, ai_image_scale)
                self.status_text.set('Error: AI image scale must be an integer in the range ]0 100]')
                logger.error(f'{this_script}: ' + 'AI image scale must be an integer in the range ]0 100]')

        except BaseException as e:

            ai_image_scale = 100 * self.configuration.ai_detection['image_width'] / self.configuration.camera['image_width']
            self.ai_image_scale_entry.delete('0', tk.END)
            self.ai_image_scale_entry.insert(tk.END, ai_image_scale)
            self.status_text.set('Error: AI image scale must be an integer in the range ]0 100]')

            logger.error(f'{this_script}: AI image scale must be an integer in the range ]0 100]')
            logger.error(f'{this_script}: ' + str(e))

    def set_awb_mode(self, event):

        if self.camera.available:

            awb_mode = self.awb_combobox.get()

            if awb_mode == 'Auto':
                awb_mode_enum = libcamera.controls.AwbModeEnum.Auto
            elif awb_mode == 'Tungsten':
                awb_mode_enum = libcamera.controls.AwbModeEnum.Tungsten
            elif awb_mode == 'Fluorescent':
                awb_mode_enum = libcamera.controls.AwbModeEnum.Fluorescent
            elif awb_mode == 'Indoor':
                awb_mode_enum = libcamera.controls.AwbModeEnum.Indoor
            elif awb_mode == 'Daylight':
                awb_mode_enum = libcamera.controls.AwbModeEnum.Daylight
            elif awb_mode == 'Cloudy':
                awb_mode_enum = libcamera.controls.AwbModeEnum.Cloudy

            self.camera.set_controls({'AwbEnable': True, 'AwbMode': awb_mode_enum})

    def save_awb_mode(self):

        awb_mode = self.awb_combobox.get()

        self.configuration.camera['white_balance']['mode'] = awb_mode

        self.configuration.save()

        self.configuration.read()

        self.update_configuration_display()

        self.status_text.set(f'New configuration saved: white balance set to {awb_mode}')
        logger.info(f'{this_script}: white balance set to {awb_mode}')

    def select_af_mode(self):

        if self.camera.available:

            lens_position = self.lens_position_scale.get()

            af_mode = self.af_mode.get()

            if af_mode == 'A':
                af_mode_enum = libcamera.controls.AfModeEnum.Auto
                lens_position = 1.0
            elif af_mode == 'C':
                af_mode_enum = libcamera.controls.AfModeEnum.Continuous
                lens_position = 1.0
                self.auto_focus_subframe_2.pack(side=tk.TOP, fill=tk.X)
                self.auto_focus_subframe_3.pack(side=tk.TOP, fill=tk.X)
                self.auto_focus_subframe_4.pack_forget()
            elif af_mode == 'M':
                af_mode_enum = libcamera.controls.AfModeEnum.Manual
                self.lens_distance.set(f'(distance  \u2243  {100/lens_position:.1f} cm)')
                self.auto_focus_subframe_2.pack_forget()
                self.auto_focus_subframe_3.pack_forget()
                self.auto_focus_subframe_4.pack(side=tk.TOP, fill=tk.X)

            af_range = self.af_range.get()

            if af_range == 'N':
                af_range_enum = libcamera.controls.AfRangeEnum.Normal
            elif af_range == 'M':
                af_range_enum = libcamera.controls.AfRangeEnum.Macro
            elif af_range == 'F':
                af_range_enum = libcamera.controls.AfRangeEnum.Full

            af_speed = self.af_speed.get()
            if af_speed == 'N':
                af_speed_enum = libcamera.controls.AfSpeedEnum.Normal
            elif af_speed == 'F':
                af_speed_enum = libcamera.controls.AfSpeedEnum.Fast

            self.camera.set_controls({'AfMode': af_mode_enum, 'LensPosition': lens_position, 'AfRange': af_range_enum, 'AfSpeed': af_speed_enum})

    def select_lens_position(self, event):

        if self.af_mode.get() == 'M':
            lens_position = self.lens_position_scale.get()

            if self.camera.available:
                self.camera.set_controls({'LensPosition': lens_position})

            if lens_position != 0:
                self.lens_distance.set(f'(distance \u2243 {100/lens_position:.1f} cm)')
            else:
                self.lens_distance.set(f'(distance inf)')

    def save_af(self):

        af_mode = self.af_mode.get()

        if af_mode == 'A':
            mode = 'Auto'
        elif af_mode == 'C':
            mode = 'Continuous'
        elif af_mode == 'M':
            mode = 'Manual'

        self.configuration.camera['autofocus']['mode'] = mode

        af_range = self.af_range.get()
        if af_range == 'N':
            rng = 'Normal'
        elif af_range == 'M':
            rng = 'Macro'
        elif af_range == 'F':
            rng = 'Full'
        self.configuration.camera['autofocus']['range'] = rng

        af_speed = self.af_speed.get()
        if af_speed == 'N':
            speed = 'Normal'
        elif af_speed == 'F':
            speed = 'Fast'
        self.configuration.camera['autofocus']['speed'] = speed

        lens_position = self.lens_position_scale.get()
        self.configuration.camera['autofocus']['lens_position'] = lens_position

        self.configuration.save()

        self.configuration.read()

        self.update_configuration_display()

        self.status_text.set(f'New configuration saved: autofocus set to {mode}')
        logger.info(f'{this_script}: autofocus set to {mode}')

    def set_image_adjustments(self, ctrl):

        if self.camera.available:

            if ctrl == 'brightness':
                value = self.brightness_scale.get()
                control = {'Brightness': value}
            elif ctrl == 'sharpness':
                value = self.sharpness_scale.get()
                control = {'Sharpness': value}
            elif ctrl == 'contrast':
                value = self.contrast_scale.get()
                control = {'Contrast': value}
            elif ctrl == 'saturation':
                value = self.saturation_scale.get()
                control = {'Saturation': value}

            self.camera.set_controls(control)

    def save_image_adjustments(self):

        value = self.brightness_scale.get()
        self.configuration.camera['image_adjustments']['brightness'] = value
        logger.info(f'{this_script}: brightness set to {value}')

        value = self.sharpness_scale.get()
        self.configuration.camera['image_adjustments']['sharpness'] = value
        logger.info(f'{this_script}: sharpness set to {value}')

        value = self.contrast_scale.get()
        self.configuration.camera['image_adjustments']['contrast'] = value
        logger.info(f'{this_script}: contrast set to {value}')

        value = self.saturation_scale.get()
        self.configuration.camera['image_adjustments']['saturation'] = value
        logger.info(f'{this_script}: saturation set to {value}')

        self.configuration.save()

        self.configuration.read()

        self.update_configuration_display()

    def select_aeg_mode(self):

        aeg_mode = self.auto_exposure_gain_enable.get()

        if aeg_mode == 'A':

            self.exposure_gain_subframe_2.pack_forget()
            self.exposure_gain_subframe_3.pack_forget()
            self.exposure_gain_subframe_4.pack_forget()
            self.exposure_gain_subframe_5.pack(side=tk.TOP, fill=tk.X)

        else:

            self.exposure_gain_subframe_2.pack(side=tk.TOP, fill=tk.X)
            self.exposure_gain_subframe_3.pack(side=tk.TOP, fill=tk.X)
            self.exposure_gain_subframe_4.pack(side=tk.TOP, fill=tk.X)
            self.exposure_gain_subframe_5.pack_forget()

        aeg_enable = True if self.auto_exposure_gain_enable.get() == 'A' else False

        analogue_gain = self.analog_gain_scale.get()
        exposure_time = self.exposure_time_scale.get()
        exposure_value = self.exposure_value_scale.get()

        aeg_mode = self.exposure_mode.get()

        if aeg_mode == 'N':
            aeg_mode_enum = libcamera.controls.AeExposureModeEnum.Normal
        elif aeg_mode == 'S':
            aeg_mode_enum = libcamera.controls.AeExposureModeEnum.Short
        elif aeg_mode == 'L':
            aeg_mode_enum = libcamera.controls.AeExposureModeEnum.Long
        elif aeg_mode == 'C':
            aeg_mode_enum = libcamera.controls.AeExposureModeEnum.Custom

        controls = {
            'AeEnable': aeg_enable,
            'AeExposureMode': aeg_mode_enum,
            'AnalogueGain': float(analogue_gain),
            'ExposureTime': int(exposure_time),
            'ExposureValue': float(exposure_value)
        }

        self.camera.set_controls(controls)

    def set_aeg_mode(self, event):

        if self.camera.available:

            if self.auto_exposure_gain_enable.get() == 'A':

                self.analog_gain_scale.configure(takefocus=False)
                self.analog_gain_scale.unbind('<ButtonRelease-1>')
                self.exposure_time_scale.configure(takefocus=False)
                self.exposure_time_scale.unbind('<ButtonRelease-1>')
                self.exposure_value_scale.configure(takefocus=False)
                self.exposure_value_scale.unbind('<ButtonRelease-1>')

                self.exposure_time_scale.configure(to=220000000)

            else:

                self.analog_gain_scale.configure(takefocus=1)
                self.analog_gain_scale.bind('<ButtonRelease-1>', self.set_aeg_mode)
                self.exposure_time_scale.configure(takefocus=1)
                self.exposure_time_scale.bind('<ButtonRelease-1>', self.set_aeg_mode)
                self.exposure_value_scale.configure(takefocus=1)
                self.exposure_value_scale.bind('<ButtonRelease-1>', self.set_aeg_mode)

                self.exposure_time_scale.configure(to=EXPOSURE_TIME_MAX)

                if self.exposure_time_scale.get() > EXPOSURE_TIME_MAX:
                    self.exposure_time_scale.set(EXPOSURE_TIME_MAX)

            aeg_enable = True if self.auto_exposure_gain_enable.get() == 'A' else False

            analogue_gain = self.analog_gain_scale.get()
            exposure_time = self.exposure_time_scale.get()
            exposure_value = self.exposure_value_scale.get()

            aeg_mode = self.exposure_mode.get()

            if aeg_mode == 'N':
                aeg_mode_enum = libcamera.controls.AeExposureModeEnum.Normal
            elif aeg_mode == 'S':
                aeg_mode_enum = libcamera.controls.AeExposureModeEnum.Short
            elif aeg_mode == 'L':
                aeg_mode_enum = libcamera.controls.AeExposureModeEnum.Long
            elif aeg_mode == 'C':
                aeg_mode_enum = libcamera.controls.AeExposureModeEnum.Custom

            controls = {
                'AeEnable': aeg_enable,
                'AeExposureMode': aeg_mode_enum,
                'AnalogueGain': float(analogue_gain),
                'ExposureTime': int(exposure_time),
                'ExposureValue': float(exposure_value)
            }

            self.camera.set_controls(controls)

    def save_aeg_mode(self):

        mode = self.auto_exposure_gain_enable.get()

        if mode == 'M':
            self.configuration.camera['exposure_gain']['mode'] = 'Manual'
        else:
            self.configuration.camera['exposure_gain']['mode'] = 'Auto'

        if self.exposure_mode.get() == 'N':
            self.configuration.camera['exposure_gain']['exposure_mode'] = 'Normal'
        elif self.exposure_mode.get() == 'S':
            self.configuration.camera['exposure_gain']['exposure_mode'] = 'Short'
        elif self.exposure_mode.get() == 'L':
            self.configuration.camera['exposure_gain']['exposure_mode'] = 'Long'

        analogue_gain = self.analog_gain_scale.get()
        exposure_time = self.exposure_time_scale.get()
        exposure_value = self.exposure_value_scale.get()

        self.configuration.camera['exposure_gain']['analog_gain'] = analogue_gain
        self.configuration.camera['exposure_gain']['exposure_time'] = exposure_time
        self.configuration.camera['exposure_gain']['exposure_value'] = exposure_value

        self.configuration.save()

        self.configuration.read()

        self.update_configuration_display()
        
        self.camera.configure(self.configuration)

        self.status_text.set(f"New configuration saved: exposure/gain mode set to {self.configuration.camera['exposure_gain']['mode']}")

        logger.info(f"{this_script}: exposure/gain set to {self.configuration.camera['exposure_gain']['mode']}")
        logger.info(f"{this_script}: exposure mode set to {self.configuration.camera['exposure_gain']['exposure_mode']}")
        logger.info(f'{this_script}: analog gain set to {analogue_gain}')
        logger.info(f'{this_script}: exposure time set to {exposure_time}')
        logger.info(f'{this_script}: exposure value set to {exposure_value}')

    def center_crop_limits(self):

        if self.camera.available:

            mode = self.configuration.camera['sensor']['mode']

            sensor_mode = self.camera.camera.sensor_modes[mode]

            width = self.crop_width_entry.get()
            height = self.crop_height_entry.get()

            x = sensor_mode['size'][0]//2 - self.crop_limits[2]//2
            y = sensor_mode['size'][1]//2 - self.crop_limits[3]//2

            try:

                self.crop_limits[0] = int(x)
                self.crop_limits[1] = int(y)
                self.crop_limits[2] = int(width)
                self.crop_limits[3] = int(height)

                self.camera.set_controls({'ScalerCrop': self.crop_limits})

                self.crop_x_entry.delete('0', tk.END)
                self.crop_x_entry.insert(0, str(x))

                self.crop_y_entry.delete('0', tk.END)
                self.crop_y_entry.insert(0, str(y))

                self.status_text.set('Image centered')

            except BaseException as e:

                self.status_text.set('Error: unable to center image')

                logger.error(f'{this_script}: ' + 'unable to center image')
                logger.error(f'{this_script}: ' + str(e))

    def set_full_size_crop_limits(self):

        if self.camera.available:

            mode = self.configuration.camera['sensor']['mode']

            sensor_mode = self.camera.camera.sensor_modes[mode]

            self.crop_limits[0] = 0
            self.crop_limits[1] = 0
            self.crop_limits[2] = sensor_mode['size'][0]
            self.crop_limits[3] = sensor_mode['size'][1]

            self.camera.set_controls({'ScalerCrop': self.crop_limits})

            self.crop_x_entry.delete('0', tk.END)
            self.crop_x_entry.insert(0, str(0))

            self.crop_y_entry.delete('0', tk.END)
            self.crop_y_entry.insert(0, str(0))

            self.crop_width_entry.delete('0', tk.END)
            self.crop_width_entry.insert(0, str(sensor_mode['size'][0]))

            self.crop_height_entry.delete('0', tk.END)
            self.crop_height_entry.insert(0, str(sensor_mode['size'][1]))

            self.status_text.set('Image full sized')

    def save_crop_limits(self):

        if self.camera.available:

            try:

                x = int(self.crop_x_entry.get())
                y = int(self.crop_y_entry.get())
                width = int(self.crop_width_entry.get())
                height = int(self.crop_height_entry.get())

                if x < 0 or x > self.camera.camera.sensor_modes[self.configuration.camera['sensor']['mode']]['size'][0]:

                    raise BaseException

                if y < 0 or y > self.camera.camera.sensor_modes[self.configuration.camera['sensor']['mode']]['size'][1]:

                    raise BaseException

                if width < 0 or width > self.camera.camera.sensor_modes[self.configuration.camera['sensor']['mode']]['size'][0]:

                    raise BaseException

                if height < 0 or height > self.camera.camera.sensor_modes[self.configuration.camera['sensor']['mode']]['size'][1]:

                    raise BaseException

                self.crop_limits[0] = x
                self.crop_limits[1] = y
                self.crop_limits[2] = width
                self.crop_limits[3] = height

                self.configuration.camera['sensor']['crop_limits'] = self.crop_limits

                self.configuration.camera['image_width'] = self.crop_limits[2]
                self.configuration.camera['image_height'] = self.crop_limits[3]

                self.configuration.save()

                self.configuration.read()

                self.update_configuration_display()

                self.image_size.set(f"Image capture size: {self.configuration.camera['image_width']}x{self.configuration.camera['image_height']}")

                self.save_ai_image_size(update_camera_configuration=False)

                self.camera.configure(self.configuration)

                self.status_text.set(f"New configuration saved: image size {self.configuration.camera['image_width']}x{self.configuration.camera['image_height']} at ({self.crop_limits[0]},{self.crop_limits[1]})")

                logger.info(f'{this_script}: image width set to {self.crop_limits[0]}')
                logger.info(f'{this_script}: image height set to {self.crop_limits[1]}')
                logger.info(f'{this_script}: image x set to {self.crop_limits[2]}')
                logger.info(f'{this_script}: image y set to {self.crop_limits[3]}')

            except BaseException as e:

                self.crop_x_entry.delete(0, tk.END)
                self.crop_x_entry.insert(0, str(self.configuration.camera['sensor']['crop_limits'][0]))
                self.crop_y_entry.delete(0, tk.END)
                self.crop_y_entry.insert(0, str(self.configuration.camera['sensor']['crop_limits'][1]))
                self.crop_width_entry.delete(0, tk.END)
                self.crop_width_entry.insert(0, str(self.configuration.camera['sensor']['crop_limits'][2]))
                self.crop_height_entry.delete(0, tk.END)
                self.crop_height_entry.insert(0, str(self.configuration.camera['sensor']['crop_limits'][3]))

                logger.error(f'{this_script}: ' + 'image size and position must positive integers')
                logger.error(f'{this_script}: ' + str(e))

                self.status_text.set(f"Error: image size and position must positive integers")

    def move_crop_limits(self, direction):

        if self.camera.available:

            try:

                displacement = int(self.crop_limits_entry.get())

                if direction == 'up':

                    self.crop_limits[1] -= displacement
                    if self.crop_limits[1] < 0:
                        self.crop_limits[1] = 0

                elif direction == 'down':

                    self.crop_limits[1] += displacement

                elif direction == 'left':

                    self.crop_limits[0] -= displacement
                    if self.crop_limits[0] < 0:
                        self.crop_limits[0] = 0

                else:

                    self.crop_limits[0] += displacement

                self.camera.set_controls({'ScalerCrop': self.crop_limits})

                self.crop_x_entry.delete('0', tk.END)
                self.crop_x_entry.insert(0, str(self.crop_limits[0]))

                self.crop_y_entry.delete('0', tk.END)
                self.crop_y_entry.insert(0, str(self.crop_limits[1]))

            except BaseException as e:

                self.crop_limits_entry.delete('0', tk.END)
                self.crop_limits_entry.insert(0, str(10))
                self.status_text.set(f"Error: motion increment must be a positive integer")

                logger.error(f'{this_script}: ' + 'motion increment must be a positive integer')
                logger.error(f'{this_script}: ' + str(e))

    def set_images_capture_mode(self, event):

        # Mode 1: Trap => LEDs Rear + LEDs Front
        # Mode 2: Lepinoc => LEDs Front + LEDs UV
        # Mode 3: Deported camera => LEDs Deported

        mode = self.images_capture_mode_combobox.get()

        if mode == 'Trap':

            self.leds_rear_scale.pack(side=tk.LEFT, padx=(5,0), pady=(0,5))
            self.leds_front_scale.pack(side=tk.LEFT, padx=(5,0), pady=(0,5))
            self.leds_deported_scale.pack_forget()
            self.leds_uv_scale.pack_forget()

        elif mode == 'Lepinoc':

            self.leds_rear_scale.pack_forget()
            self.leds_front_scale.pack(side=tk.LEFT, padx=(5,0), pady=(0,5))
            self.leds_deported_scale.pack_forget()
            self.leds_uv_scale.pack(side=tk.LEFT, padx=(5,0), pady=(0,5))

        elif mode == 'Deported':

            self.leds_rear_scale.pack_forget()
            self.leds_front_scale.pack_forget()
            self.leds_deported_scale.pack(side=tk.LEFT, padx=(5,0), pady=(0,5))
            self.leds_uv_scale.pack_forget()

    def save_images_capture_jpeg_quality(self):

        jpeg_quality = self.images_capture_jpeg_entry.get()

        try:

            jpeg_quality = int(jpeg_quality)

            if jpeg_quality >= 0 and jpeg_quality <= 100:

                self.configuration.files['jpeg_quality'] = jpeg_quality

                self.camera.configure(self.configuration)

                self.configuration.save()

                self.configuration.read()

                self.update_configuration_display()

                logger.info(f'{this_script}: jpeg quality set to {jpeg_quality} %')

                self.status_text.set(f'New configuration saved: jpeg quality set to {jpeg_quality} %')

            else:

                self.images_capture_jpeg_entry.delete('0', tk.END)
                self.images_capture_jpeg_entry.insert(tk.END, self.configuration.files['jpeg_quality'])
                self.status_text.set('Error: JPEG quality must be a positive integer in the range [0 100]')
                logger.error(f'{this_script}: ' + 'JPEG quality must be a positive integer in the range [0 100]')

        except BaseException as e:

            self.images_capture_jpeg_entry.delete('0', tk.END)
            self.images_capture_jpeg_entry.insert(tk.END, self.configuration.files['jpeg_quality'])
            self.status_text.set('Error: JPEG quality must be a positive integer in the range [0 100]')

            logger.error(f'{this_script}: ' + 'JPEG quality must be a positive integer in the range [0 100]')
            logger.error(f'{this_script}: ' + str(e))

    def save_images_capture_mode(self):

        mode = self.images_capture_mode_combobox.get()

        if mode == 'Trap':
            self.configuration.leds['mode'] = 1
        elif mode == 'Lepinoc':
            self.configuration.leds['mode'] = 2
        elif mode == 'Deported':
            self.configuration.leds['mode'] = 3

        self.configuration.save()

        self.configuration.read()

        self.update_configuration_display()

        self.status_text.set(f'New configuration saved: image capture mode set to {mode}')

        logger.info(f'{this_script}: image capture mode set to {mode}')

    def set_leds_intensity(self, leds):

        if leds == 'rear':
            intensity = self.leds_rear_scale.get()
            self.leds_rear.set_intensity(intensity)
            self.leds_rear.turn_on()
        elif leds == 'front':
            intensity = self.leds_front_scale.get()
            self.leds_front.set_intensity(intensity)
            self.leds_front.turn_on()
        elif leds == 'uv':
            intensity = self.leds_uv_scale.get()
            self.leds_uv.set_intensity(intensity)
            self.leds_uv.turn_on()
        elif leds == 'deported':
            intensity = self.leds_deported_scale.get()
            self.leds_deported.set_intensity(intensity)
            self.leds_deported.turn_on()

    def save_leds_intensity(self):

        mode = self.images_capture_mode_combobox.get()

        if mode == 'Trap':

            self.configuration.leds['intensity_rear'] = self.leds_rear_scale.get()
            self.configuration.leds['intensity_front'] = self.leds_front_scale.get()
            self.configuration.leds['intensity_uv'] = 0
            self.leds_uv_scale.set(0)
            self.configuration.leds['intensity_deported'] = 0
            self.leds_deported_scale.set(0)

            self.set_leds_intensity('front')
            self.set_leds_intensity('rear')

            logger.info(f'{this_script}: front LEDs intensity set to {self.leds_front_scale.get()} %')
            logger.info(f'{this_script}: rear LEDs intensity set to {self.leds_rear_scale.get()} %')

            self.status_text.set(f'New configuration saved: front LEDs intensity {self.leds_front_scale.get()} % and rear LEDs intensity {self.leds_rear_scale.get()} %')

        elif mode == 'Lepinoc':

            self.configuration.leds['intensity_rear'] = 0
            self.leds_rear_scale.set(0)
            self.configuration.leds['intensity_front'] = self.leds_front_scale.get()
            self.configuration.leds['intensity_uv'] = self.leds_uv_scale.get()
            self.configuration.leds['intensity_deported'] = 0
            self.leds_deported_scale.set(0)

            self.set_leds_intensity('front')
            self.set_leds_intensity('uv')

            logger.info(f'{this_script}: front LEDs intensity set to {self.leds_front_scale.get()} %')
            logger.info(f'{this_script}: uv LEDs intensity set to {self.leds_uv_scale.get()} %')

            self.status_text.set(f'New configuration saved: front LEDs intensity {self.leds_front_scale.get()} % and uv LEDs intensity {self.leds_uv_scale.get()} %')

        elif mode == 'Deported':

            self.configuration.leds['intensity_rear'] = 0
            self.leds_rear_scale.set(0)
            self.configuration.leds['intensity_front'] = 0
            self.leds_front_scale.set(0)
            self.configuration.leds['intensity_uv'] = 0
            self.leds_uv_scale.set(0)
            self.configuration.leds['intensity_deported'] = self.leds_deported_scale.get()

            self.set_leds_intensity('front')
            self.set_leds_intensity('deported')

            logger.info(f'{this_script}: deported LEDs intensity set to {self.leds_deported_scale.get()} %')

            self.status_text.set(f'New configuration saved: deported LEDs intensity {self.leds_deported_scale.get()} %')

        self.configuration.save()

        self.configuration.read()

        self.update_configuration_display()

    def save_leds_delay(self):
        
        leds_delay_on = self.leds_delay_on_entry.get()
        leds_delay_off = self.leds_delay_off_entry.get()

        try:

            leds_delay_on = float(leds_delay_on)
            leds_delay_off = float(leds_delay_off)

            if leds_delay_on >= 0 and leds_delay_off >= 0:

                self.configuration.leds['delay_on'] = leds_delay_on
                self.configuration.leds['delay_off'] = leds_delay_off

                self.configuration.save()

                self.configuration.read()

                self.update_configuration_display()

                self.status_text.set(f'New configuration saved: LEDs delays set to {leds_delay_on}s (on) and {leds_delay_off}s (off)')
                logger.info(f'{this_script}: LEDs delays set to {leds_delay_on}s (on) and {leds_delay_off}s (off)')

            else:

                self.leds_delay_on_entry.delete('0', tk.END)
                self.leds_delay_on_entry.insert(tk.END, self.configuration.leds['delay_on'])
                self.leds_delay_off_entry.delete('0', tk.END)
                self.leds_delay_off_entry.insert(tk.END, self.configuration.leds['delay_off'])
                self.status_text.set('Error: LEDs delays must be >= 0')
                logger.error(f'{this_script}: LEDs delays must be >= 0')

        except BaseException as e:

            self.leds_delay_on_entry.delete('0', tk.END)
            self.leds_delay_on_entry.insert(tk.END, self.configuration.leds['delay_on'])
            self.leds_delay_off_entry.delete('0', tk.END)
            self.leds_delay_off_entry.insert(tk.END, self.configuration.leds['delay_off'])
            
            self.status_text.set('Error: LEDs delays must be >= 0')
            logger.error(f'{this_script}: LEDs delays must be >= 0')
            logger.error(f'{this_script}: ' + str(e))

    def update_ui(self):

        global image_tk_3 # Workaround

        if self.image_lock:

            self.preview_label.config(image=self.image_tk_2)

            image_tk_3 = self.image_tk_2

            elapsed_time = time.time() - self.last_time
            current_fps = f'Preview FPS: {int(1/elapsed_time):02d}'
            self.fps.set(current_fps)
            self.last_time = time.time()

            self.image_lock = False

        if SHOW_PERF:
            print(f'Preview FPS {(time.perf_counter_ns() - start_time)/1E9}')

        if SHOW_PERF:
            print('')

        if time.time() - self.last_time_cpu_temp > CPU_TEMP_INTERVAL:

            self.last_time_cpu_temp = time.time()
            self.cpu_temp_str.set(f"CPU Temperature: {rpi.get_temperature():.1f} \u00B0C (must be less than 80 \u00B0C)")

        self.after(UPDATE_UI_INTERVAL_IN_MS, self.update_ui)

def main():

    tk_interface = TkInterface()

    tk_interface.mainloop()

if __name__ == '__main__':

    main()

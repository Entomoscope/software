import time
import sys
import os
from math import tan, pi
from json import dump

import logging
from logging.handlers import RotatingFileHandler

import traceback

import io
from threading import Condition

import libcamera

from picamera2 import Picamera2, Controls
from picamera2.encoders import MJPEGEncoder, JpegEncoder, H264Encoder
from picamera2.outputs import FileOutput

import numpy as np

from cv2 import imencode, IMWRITE_JPEG_QUALITY, cvtColor, COLOR_YUV420p2RGB

sys.path.append('..')

from globals_parameters import LOGS_DESKTOP_FOLDER, TODAY, CAMERA_PREVIEW_FPS

this_script = os.path.basename(__file__)[:-3]

today_log_path = os.path.join(LOGS_DESKTOP_FOLDER, TODAY)
if not os.path.exists(today_log_path):
    os.mkdir(today_log_path)

picamera2_logger = logging.getLogger('picamera2')
filename = os.path.join(today_log_path, TODAY + '_picamera2.log')
file_handler = RotatingFileHandler(filename, mode="a", maxBytes=10000, backupCount=100, encoding="utf-8")
picamera2_logger.addHandler(file_handler)
formatter = logging.Formatter('%(asctime)s.%(msecs)03d;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
file_handler.setFormatter(formatter)
picamera2_logger.setLevel("INFO")

os.environ['LIBCAMERA_LOG_FILE'] = os.path.join(today_log_path, TODAY + '_libcamera.log')
os.environ['LIBCAMERA_LOG_LEVELS'] = '1'

logger = logging.getLogger('entomoscope_camera_2')
filename = os.path.join(today_log_path, TODAY + '_' + this_script + '.log')
file_handler = RotatingFileHandler(filename, mode="a", maxBytes=10000, backupCount=100, encoding="utf-8")
logger.addHandler(file_handler)
formatter = logging.Formatter('%(asctime)s.%(msecs)03d;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
file_handler.setFormatter(formatter)
logger.setLevel("DEBUG")

PREVIEW_WIDTH_MAX = 885
PREVIEW_HEIGHT_MAX = 500

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

class Camera2():

    encode_param = [int(IMWRITE_JPEG_QUALITY), 100]

    def __init__(self, camera_index=0, configuration=None, mode='detection', verbose=False, perf=False):

        try:

            logger.info('***************')
            logger.info('initialising camera')

            try:

                self.camera = Picamera2(camera_index)
                camera_found = True

            except IndexError as e:

                camera_found = False

                logger.error(f'camera not found (index={camera_index}')

            if camera_found:

                self.camera_index = camera_index
                self.camera_config = None
                self.model = self.camera.camera_properties['Model'].lower()

                logger.info(f'camera model {self.model } found')

                self.started = False
                self.encoder_started = False

                self.configured = False

                self.autofocus_available = False

                self.frame_data = None
                self.metadata = None
                self.jpeg_data = None

                self.mode = mode

                self.overlay = None

                self.perf = perf
                self.verbose = verbose

                if configuration:

                    try:

                        self.configure(configuration)

                    except BaseException as e:

                        logger.error('configuration error')
                        logger.error(str(e))
                        print(traceback.format_exc())

                self.available = True

                logger.info('camera initialised')

            else:

                self.available = False

                logger.info('camera not initialised')

        except IndexError as e:

            logger.error('camera not initialised - bad index')
            logger.error(str(e))

            self.camera = None
            self.available = False
            self.configured = False
            self.autofocus_available = False
            self.is_camera_supported = False
            self.autofocus_available = False

    def configure(self, configuration, align_configuration=False):

        self.is_camera_supported = False
        self.autofocus_available = False

        # https://www.raspberrypi.com/documentation/accessories/camera.html#hardware-specification
        if configuration.camera['model'].lower() == 'v3' and self.model == 'imx708':
            self.is_camera_supported = True
            self.autofocus_available = True
            self.sensor_resolution = self.get_sensor_resolution() # (4608, 2592)
        elif configuration.camera['model'].lower() == 'v2' and self.model == 'imx219':
            self.is_camera_supported = True
            self.autofocus_available = False
            self.sensor_resolution = self.get_sensor_resolution() # (3280, 2464)
        elif configuration.camera['model'].lower() == 'v1' and self.model == 'ov5647':
            self.is_camera_supported = True
            self.autofocus_available = False
            self.sensor_resolution = self.get_sensor_resolution() # (2592, 1944)
        elif configuration.camera['model'].lower() == 'hq' and self.model == 'imx477':
            self.is_camera_supported = True
            self.autofocus_available = False
            self.sensor_resolution = self.get_sensor_resolution() # (4056, 3040)

        if self.is_camera_supported:

            if self.started:
                self.camera.stop()
                need_to_restart = True
            else:
                need_to_restart = False

            controls = Controls(self.camera)

            awb_mode = configuration.camera['auto_white_balance']['mode']

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

            af_mode = libcamera.controls.AfModeEnum.Manual if configuration.camera['autofocus']['mode']=='Manual' else libcamera.controls.AfModeEnum.Auto if configuration.camera['autofocus']['mode']=='Auto' else libcamera.controls.AfModeEnum.Continuous
            af_range = libcamera.controls.AfRangeEnum.Normal if configuration.camera['autofocus']['range']=='Normal' else libcamera.controls.AfRangeEnum.Macro if configuration.camera['autofocus']['range']=='Macro' else libcamera.controls.AfRangeEnum.Full
            af_speed = libcamera.controls.AfSpeedEnum.Normal if configuration.camera['autofocus']['speed']=='Normal' else libcamera.controls.AfSpeedEnum.Fast
            ae_exposure_mode = libcamera.controls.AeExposureModeEnum.Normal if configuration.camera['auto_exposure_gain']['exposure_mode'] == 'Normal' else libcamera.controls.AeExposureModeEnum.Short if configuration.camera['exposure_gain']['exposure_mode'] == 'Short' else libcamera.controls.AeExposureModeEnum.Long

            controls.AwbEnable = configuration.camera['auto_white_balance']['enable']
            controls.AwbMode = awb_mode_enum
            # controls.ColourGains = configuration.camera['white_balance']['colour_gains']
            if self.autofocus_available:
                controls.LensPosition = configuration.camera['autofocus']['lens_position']
                controls.AfMode = af_mode
                controls.AfRange = af_range
                controls.AfSpeed = af_speed
            if self.mode == 'detection':
                controls.ScalerCrop = configuration.camera['sensor']['crop_limits']
            else:
                controls.ScalerCrop = [0, 0] + list(self.get_sensor_resolution())
            controls.AeEnable = configuration.camera['auto_exposure_gain']['mode'] == 'Auto'
            if controls.AeEnable:
                controls.AeExposureMode = ae_exposure_mode
                # https://forums.kinograph.cc/t/picamera2-autoexposure-question/2599/10
                controls.ExposureTime = 0
            else:
                controls.AnalogueGain = configuration.camera['auto_exposure_gain']['analogue_gain']
                controls.ExposureTime = configuration.camera['auto_exposure_gain']['exposure_time']
                controls.ExposureValue = configuration.camera['auto_exposure_gain']['exposure_value']

            controls = controls.make_dict()

            image_width = configuration.camera['image_width']
            image_height = configuration.camera['image_height']

            if self.mode == 'detection':

                sensor_mode = self.camera.sensor_modes[configuration.camera['sensor']['capture_mode']]

                main_format = 'RGB888'
                main_size = (image_width, image_height)

                lores_format = 'YUV420'
                lores_size = (configuration.ai_detection['image_width'], configuration.ai_detection['image_height'])

                self.camera_config = self.camera.create_still_configuration(sensor={'output_size': sensor_mode['size'], 'bit_depth': sensor_mode['bit_depth']},
                                                                        main={'format': main_format, 'size': main_size},
                                                                        lores={'format': lores_format, 'size': lores_size},
                                                                        raw=None, # no need,
                                                                        display=None,
                                                                        encode=None,
                                                                        transform=libcamera.Transform(vflip=True, hflip=True),
                                                                        buffer_count=2, # speed up capture_array()
                                                                        controls=controls)

                self.set_encode_parameter(configuration.files['jpeg_quality'])

                try:

                    self.camera_configure()
                    self.configured = True

                    logger.info('camera configured for detection')
                    logger.info(f'main format {main_format}')
                    logger.info(f'main size {main_size}')
                    logger.info(f'lores format {lores_format}')
                    logger.info(f'lores size {lores_size}')

                except BaseException as e:

                    logger.error('camera not configured')
                    logger.error(str(e))
                    self.configured = False

            else:

                sensor_mode = self.camera.sensor_modes[configuration.camera['sensor']['preview_mode']]

                main_format = 'RGB888'
                main_size = self.get_sensor_resolution()

                lores_format = 'YUV420'
                lores_size = (configuration.camera['sensor']['width_preview'], configuration.camera['sensor']['height_preview'])

                self.camera_config = self.camera.create_video_configuration(sensor={'output_size': sensor_mode['size'], 'bit_depth': sensor_mode['bit_depth']},
                                                                            main={'format': main_format, 'size': main_size},
                                                                            lores={'format': lores_format, 'size': lores_size},
                                                                            raw=None, # no need,
                                                                            display=None,
                                                                            transform=libcamera.Transform(vflip=True, hflip=True),
                                                                            buffer_count=2, # speed up capture_array()
                                                                            controls=controls,
                                                                            encode='lores')

                try:

                    self.camera_configure()
                    self.configured = True

                    self.set_encode_parameter(configuration.files['jpeg_quality'])

                    logger.info('camera configured for preview')
                    logger.info(f'main format {main_format}')
                    logger.info(f'main size {main_size}')
                    logger.info(f'lores format {lores_format}')
                    logger.info(f'lores size {lores_size}')

                except BaseException as e:

                    logger.error('camera not configured')
                    logger.error(str(e))
                    self.configured = False

                try:

                    self.encoder = MJPEGEncoder(None)
                    self.encoder.format = "YUV420"
                    self.encoder.framerate = CAMERA_PREVIEW_FPS * 3
                    self.streamOut = StreamingOutput()
                    self.streamOut2 = FileOutput(self.streamOut)
                    self.encoder.output = [self.streamOut2]

                    logger.info('MJPEG encoder set')

                except BaseException as e:

                    logger.error('MJPEG encoder not set')
                    logger.error(str(e))
                    self.configured = False

            if need_to_restart:
                self.camera.start()

        else:

            logger.error('camera not supported')
            self.configured = False

    # def is_camera_supported(self):

        # # https://www.raspberrypi.com/documentation/accessories/camera.html#hardware-specification

        # return self.supported

    # def is_autofocus_available(self):

        # # https://www.raspberrypi.com/documentation/accessories/camera.html#hardware-specification

        # autofocus_available = False

        # if self.configured:

            # if configuration.camera['model'].lower() == 'v3' and self.model == 'imx708':
                # # https://github.com/raspberrypi/linux/blob/rpi-6.6.y/drivers/media/i2c/imx708.c
                # autofocus_available = True
            # elif configuration.camera['model'].lower() == 'v2' and self.model == 'imx219':
                # # https://github.com/raspberrypi/linux/blob/rpi-6.6.y/drivers/media/i2c/imx219.c
                # autofocus_available = False
            # elif configuration.camera['model'].lower() == 'v1' and self.model == 'ov5647':
                # # https://github.com/raspberrypi/linux/blob/rpi-6.6.y/drivers/media/i2c/ov5647.c
                # autofocus_available = False
            # elif configuration.camera['model'].lower() == 'hq' and self.model == 'imx477':
                # # https://github.com/raspberrypi/linux/blob/rpi-6.6.y/drivers/media/i2c/imx477.c
                # autofocus_available = False

        # return autofocus_available

    def start(self):

        try:

            if not self.started:

                if self.mode == 'preview':

                    try:
                        self.camera.start_encoder(self.encoder)
                        self.encoder_started = True
                        logger.info('encoder started')
                    except BaseException as e:
                        self.encoder_started = False
                        logger.error('encoder not started')
                        logger.error(str(e))
                        print(traceback.format_exc())

                    if self.encoder_started:
                        self.camera.start()
                        self.started = True
                        logger.info('camera started')
                    else:
                        logger.error('camera not started')

                else:

                    self.camera.start()
                    self.started = True
                    logger.info('camera started')
            else:

                logger.info('camera already started')

        except BaseException as e:

            logger.error('camera not started')
            logger.error(str(e))
            print(traceback.format_exc())

    def stop(self):

        try:

            if self.started:

                if self.mode == 'preview':
                    if self.encoder_started:
                        try:
                            self.camera.stop_encoder(self.encoder)
                            self.encoder_started = False
                            logger.info('encoder stopped')
                        except BaseException as e:
                            logger.error('encoder not stopped')
                            logger.error(str(e))
                            print(traceback.format_exc())

                # self.camera.close()
                self.camera.stop()
                self.started = False
                logger.info('camera stopped')

            else:

                logger.info('camera already stopped')

        except BaseException as e:

            logger.error('camera not stopped')
            logger.error(str(e))
            print(traceback.format_exc())


    def close(self):

        try:

            self.camera.close()
            logger.info('camera closed')

        except BaseException as e:

            logger.error('camera not closed')
            logger.error(str(e))
            print(traceback.format_exc())


    def camera_configure(self):

        try:

            self.camera.configure(self.camera_config)

        except BaseException as e:

            logger.error(str(e))
            print(traceback.format_exc())


    def get_preview_frame(self):

        with self.streamOut.condition:
            self.streamOut.condition.wait()
            self.frame = self.streamOut.frame

            self.metadata = self.camera.capture_metadata()

        return self.frame, self.metadata

    # def get_preview_main_size(self, crop_limits, configuration):

        # # sensor_mode = self.camera.sensor_modes[configuration.camera['sensor']['preview_mode']]

        # # sensor_mode_max = self.camera.sensor_modes[-1]

        # # print(sensor_mode_max)

        # # image_width = int(crop_limits[2] / sensor_mode_max['size'][0] * sensor_mode['size'][0])
        # # image_height = int(crop_limits[3] / sensor_mode_max['size'][1] * sensor_mode['size'][1])

        # # print(f'{image_width} x {image_height}')

        # # # Width and height should be even
        # # image_width = image_width // 2 * 2
        # # image_height = image_height // 2 * 2

        # image_width = int(crop_limits[2]) // 2 * 2
        # image_height = int(crop_limits[3]) // 2 * 2

        # return image_width, image_height

    # def get_preview_lores_size(self, crop_limits, configuration):

        # width = int(crop_limits[2] / self.sensor_resolution[0] * configuration.camera['sensor']['width_preview'])
        # height = int(crop_limits[3] / self.sensor_resolution[1] * configuration.camera['sensor']['height_preview'])

        # # Width and height should be even
        # width = width // 2 * 2
        # height = height // 2 * 2

        # return width, height

    def capture(self, stream='main', flush=True, get_metadata=True):

        if self.started:

            if self.perf:
                s = time.perf_counter_ns()

            request = self.camera.capture_request(flush=flush)

            if stream == 'main' or 'both':
                self.frame_data_main = request.make_array('main')
            else:
                self.frame_data_main = None

            if stream == 'lores' or 'both':
                self.frame_data_lores = cvtColor(request.make_array('lores'), COLOR_YUV420p2RGB)
            else:
                self.frame_data_lores = None

            if get_metadata:
                self.metadata = request.get_metadata()
            else:
                self.metadata = None

            request.release()

            if self.perf:
                logger.info(f'capture {stream} in {(time.perf_counter_ns() - s)/1E9:.3f} seconds')

    def get_frame(self, stream='main'):

        if stream == 'lores':
            return self.frame_data_lores
        else:
            return self.frame_data_main

    def frame_to_jpeg(self, stream='main', crop=None):

        if self.perf:
            s = time.perf_counter_ns()

        if stream == 'lores':
            self.jpeg_data = imencode('.jpg', self.frame_data_lores, self.encode_param)[1].tobytes()
        elif stream == 'main':
            self.jpeg_data = imencode('.jpg', self.frame_data_main, self.encode_param)[1].tobytes()
        else:
            self.jpeg_data = None

        # if stream == 'lores':
            # if crop:
                # self.jpeg_data = imencode('.jpg', self.frame_data_lores[crop[0]:crop[1],crop[2]:crop[3],:], self.encode_param)[1].tobytes()
            # else:
                # self.jpeg_data = imencode('.jpg', self.frame_data_lores, self.encode_param)[1].tobytes()
        # else:
            # if crop:
                # self.jpeg_data = imencode('.jpg', self.frame_data_main[crop[0]:crop[1],crop[2]:crop[3],:], self.encode_param)[1].tobytes()
            # else:
                # self.jpeg_data = imencode('.jpg', self.frame_data_main, self.encode_param)[1].tobytes()

        if self.perf:
            logger.info(f'frame to JPEG {(time.perf_counter_ns() - s)/1E9}')

    def save_capture(self, file_path, save_metadata=True, extra_metadata=None):

        if file_path.endswith('.jpeg') or file_path.endswith('.jpg'):
            jpeg_file_path = file_path
            json_file_path = jpeg_file_path.replace('.jpeg', '.json').replace('.jpg', '.json')
        else:
            jpeg_file_path = file_path + '.jpg'
            json_file_path = jpeg_file_path.replace('.jpg', '.json')

        self.save_jpeg(jpeg_file_path)

        if save_metadata:
            self.save_json(json_file_path, extra_metadata)
        else:
            json_file_path = ''

        return jpeg_file_path, json_file_path

    def save_jpeg(self, jpeg_file_path):

        if self.jpeg_data:

            try:

                with open(jpeg_file_path, 'wb') as f:
                    f.write(self.jpeg_data)

            except BaseException as e:

                logger.error(str(e))

    def save_json(self, json_file_path, extra_metadata=None):

        if self.metadata:

            try:

                if extra_metadata:
                    metadata = {}
                    metadata.update(self.metadata)
                    metadata.update(extra_metadata)
                else:
                    metadata = self.metadata

                with open(json_file_path, 'w') as f:
                    dump(metadata, f, indent=4, sort_keys=True, separators=(',', ': '))

            except BaseException as e:

                logger.error(str(e))

    def get_controls(self):

        return self.camera.camera_controls

    def get_properties(self):

        return self.camera.camera_properties

    def get_model(self):

        return self.camera.camera_properties['Model']

    def get_metadata(self):

        return self.camera.capture_metadata()

    def set_controls(self, control):

        self.camera.set_controls(control)

    def set_encode_parameter(self, param_value):

        self.encode_param[1] = param_value
        logger.info(f'JPEG quality set to {self.encode_param[1] } %')

    def set_auto_white_balance(self, awb_enable, awb_mode='Auto'):

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

        control = {'AwbEnable': awb_enable, 'AwbMode': awb_mode_enum}
        self.set_control(control)

    def get_fov_size(self, distance):

        # TODO - Never finished or tested

        self.fov = configuration.camera['fov']

        horizontal_size = tan(self.fov[0] * pi / 180 / 2) * distance * 2
        vertical_size = tan(self.fov[1] * pi / 180 / 2) * distance * 2

        # print(f'{horizontal_size} {vertical_size}')

        return horizontal_size, vertical_size

    def get_model_sensor_resolution(self, model):

        if model.lower() == 'v3':
            sensor_resolution = (4608, 2592)
        elif model.lower() == 'v2':
            sensor_resolution = (3280, 2464)
        elif model.lower() == 'v1':
            sensor_resolution = (2592, 1944)
        elif model.lower() == 'hq':
            sensor_resolution = (4056, 3040)

        return sensor_resolution

    def get_sensor_resolution(self):

        return self.camera.camera_properties['PixelArraySize']

    def get_model_preview_resolution(self, model):

        if model.lower() == 'v3':
            preview_resolution = (1920, 1080)
        elif model.lower() == 'v2':
            preview_resolution = (1440, 1080)
        elif model.lower() == 'v1':
            preview_resolution = (1440, 1080)
        elif model.lower() == 'hq':
            preview_resolution = (1920, 1440)

        return preview_resolution

    def get_autofocus_available(self, model):

        if model.lower() == 'v3':
            autofocus_available = False
        elif model.lower() == 'v2':
            autofocus_available = False
        elif model.lower() == 'v1':
            autofocus_available = False
        elif model.lower() == 'hq':
            autofocus_available = False

        return autofocus_available

    def get_sensor_mode(self, model):

        if model.lower() == 'v3':
            preview_mode = 2
            capture_mode = 2
        elif model.lower() == 'v2':
            preview_mode = 2
            capture_mode = 2
        elif model.lower() == 'v1':
            preview_mode = 2
            capture_mode = 2
        elif model.lower() == 'hq':
            preview_mode = 3
            capture_mode = 3

        return preview_mode, capture_mode

    def __str__(self):

        s = '\nCamera properties\n\n'
        for key, value in self.camera.camera_properties.items():

            s += f'  {key}: {value}\n'

        s += '\nCamera controls\n\n'
        for key, value in self.camera.camera_controls.items():

            s += f'  {key}: {value}\n'

        s += '\nSensor modes\n'
        for sensor_mode in self.camera.sensor_modes:

            s += '\n'

            for key, value in sensor_mode.items():

                s += f'  {key}: {value}\n'

        return s

if __name__ == '__main__':

    camera = Camera2(0)

    if camera.available:

        print(camera)

        camera.stop()

    else:

        print('No camera found')

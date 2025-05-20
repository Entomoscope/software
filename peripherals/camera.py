import time
import sys
import os
from math import tan, pi
from json import dump

import logging

import libcamera

from picamera2 import Picamera2, Controls

from cv2 import imencode, IMWRITE_JPEG_QUALITY, cvtColor, COLOR_YUV420p2RGB

sys.path.append('..')

from globals_parameters import LOGS_FOLDER, TODAY

picamera2_logger = logging.getLogger('picamera2')
picamera2_logger.setLevel(logging.INFO)
h = logging.FileHandler(os.path.join(LOGS_FOLDER, TODAY + '_picamera2.log'))
f = logging.Formatter('%(asctime)s;%(levelname)s;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
h.setFormatter(f)
picamera2_logger.addHandler(h)

os.environ['LIBCAMERA_LOG_FILE'] = os.path.join(LOGS_FOLDER, TODAY + '_libcamera.log')
os.environ['LIBCAMERA_LOG_LEVELS'] = '1'

this_script = os.path.basename(__file__)[:-3]

logger = logging.getLogger('entomoscope_camera')
logger.setLevel(logging.INFO)
h = logging.FileHandler(os.path.join(LOGS_FOLDER, TODAY + '_' + this_script + '.log'))
f = logging.Formatter('%(asctime)s;%(levelname)s;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
h.setFormatter(f)
logger.addHandler(h)

PREVIEW_WIDTH_MAX = 885
PREVIEW_HEIGHT_MAX = 500

class Camera():

    encode_param = [int(IMWRITE_JPEG_QUALITY), 90]

    def __init__(self, camera_number=0, configuration=None, mode='detection', verbose=False, perf=False):

        try:

            self.camera = Picamera2(camera_number)
            self.camera_number = camera_number
            self.camera_config = None
            self.model = self.camera.camera_properties['Model'].lower()
            self.started = False

            self.configured = False

            self.autofocus_available = False

            self.frame_data = None
            self.metadata = None
            self.jpeg_data = None

            self.mode = mode

            self.perf = perf
            self.verbose = verbose

            if configuration:
                self.configure(configuration)

            self.available = True

            logger.info(f'{this_script}: Camera initialised')

        except IndexError as e:

            logger.error(f'{this_script}: Camera not initialised - Bad index')
            logger.error(str(e))

            self.camera = None
            self.available = False

    def configure(self, configuration, align_configuration=False):

        self.is_camera_supported = False
        self.autofocus_available = False

        if configuration.camera['model'].lower() == 'v3' and self.model == 'imx708':
            self.is_camera_supported = True
            self.autofocus_available = True
            self.sensor_resolution = (4608, 2592)
        elif configuration.camera['model'].lower() == 'v2' and self.model == 'imx219':
            self.is_camera_supported = True
            self.autofocus_available = False
            self.sensor_resolution = (3280, 2464)
        elif configuration.camera['model'].lower() == 'v1' and self.model == 'ov5647':
            self.is_camera_supported = True
            self.autofocus_available = False
            self.sensor_resolution = (2592, 1944)
        elif configuration.camera['model'].lower() == 'hq' and self.model == 'imx477':
            self.is_camera_supported = True
            self.autofocus_available = False
            self.sensor_resolution = (4056, 3040)
        self.image_ratio = self.sensor_resolution[0] / self.sensor_resolution[1]

        if self.is_camera_supported:

            if self.started:
                self.camera.stop()
                need_to_restart = True
            else:
                need_to_restart = False

            sensor_mode = self.camera.sensor_modes[configuration.camera['sensor']['mode']]

            controls = Controls(self.camera)

            awb_mode = configuration.camera['white_balance']['mode']

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
            ae_exposure_mode = libcamera.controls.AeExposureModeEnum.Normal if configuration.camera['exposure_gain']['exposure_mode'] == 'Normal' else libcamera.controls.AeExposureModeEnum.Short if configuration.camera['exposure_gain']['exposure_mode'] == 'Short' else libcamera.controls.AeExposureModeEnum.Long

            controls.AwbEnable = configuration.camera['white_balance']['enable']
            controls.AwbMode = awb_mode_enum
            # controls.ColourGains = configuration.camera['white_balance']['colour_gains']
            if self.autofocus_available:
                controls.LensPosition = configuration.camera['autofocus']['lens_position']
                controls.AfMode = af_mode
                controls.AfRange = af_range
                controls.AfSpeed = af_speed
            controls.ScalerCrop = configuration.camera['sensor']['crop_limits']
            controls.AeEnable = configuration.camera['exposure_gain']['mode'] == 'Auto'
            controls.AeExposureMode = ae_exposure_mode
            controls.AnalogueGain = configuration.camera['exposure_gain']['analog_gain']
            controls.ExposureTime = configuration.camera['exposure_gain']['exposure_time']
            controls.ExposureValue = configuration.camera['exposure_gain']['exposure_value']

            controls = controls.make_dict()

            image_width = configuration.camera['image_width']
            image_height = configuration.camera['image_height']

            if self.mode == 'detection':

                main_format = 'RGB888'
                main_size = (image_width, image_height)
                lores_format = 'YUV420'
                lores_size = (configuration.ai_detection['image_width'], configuration.ai_detection['image_height'])

            else:

                main_format = 'RGB888'
                main_size = (image_width, image_height)

                lores_format = 'YUV420'

                # PREVIEW_HEIGHT_MAX = int(PREVIEW_WIDTH_MAX // self.image_ratio)
                PREVIEW_WIDTH_MAX = int(PREVIEW_HEIGHT_MAX * self.image_ratio)

                # print(f'O {main_size[0]} {main_size[1]} {PREVIEW_WIDTH_MAX} {PREVIEW_HEIGHT_MAX} {self.image_ratio}')

                if image_width > PREVIEW_WIDTH_MAX and image_height > PREVIEW_HEIGHT_MAX:

                    # print('Shrink W&H')

                    scale_factor_width = PREVIEW_WIDTH_MAX / image_width
                    scale_factor_height = PREVIEW_HEIGHT_MAX / image_height
                    scale = scale_factor_width if scale_factor_width <= scale_factor_height else scale_factor_height

                    # print(f'{scale_factor_width} {scale_factor_height} {scale}')

                    lores_width = int(scale * image_width)
                    lores_height = int(scale * image_height)

                elif image_height > PREVIEW_HEIGHT_MAX:

                    # print('Shrink H')

                    lores_width = int(image_width * PREVIEW_WIDTH_MAX // image_height)
                    lores_height = PREVIEW_HEIGHT_MAX

                    if lores_width > PREVIEW_WIDTH_MAX:

                        lores_height = int(lores_height * PREVIEW_WIDTH_MAX // lores_width)
                        lores_width = PREVIEW_WIDTH_MAX

                elif image_width > PREVIEW_WIDTH_MAX:

                    # print('Shrink H')

                    lores_height = int(image_height * self.TK_IMAGE_WIDTH_MAX // image_width)
                    lores_width = PREVIEW_WIDTH_MAX

                    if lores_height > PREVIEW_HEIGHT_MAX:

                        lores_width = int(lores_width * PREVIEW_HEIGHT_MAX // lores_height)
                        lores_height = PREVIEW_HEIGHT_MAX

                elif image_width < PREVIEW_WIDTH_MAX and image_height < PREVIEW_HEIGHT_MAX:

                    # print('Zoom')

                    lores_width = image_width
                    lores_height = image_height

                # print(f'F {image_width} {image_height} L {lores_width} {lores_height} M {PREVIEW_WIDTH_MAX} {PREVIEW_HEIGHT_MAX}')

                # Multiple of 64 for lores with YUV420 format
                # See "Appendix A: Pixel and image formats" in the Picamera2 library documentation

                lores_width = ((lores_width - 1) // 64) * 64
                lores_height = ((lores_height - 1) // 64) * 64

                # print(f'C {image_width} {image_height} L {lores_width} {lores_height} M {PREVIEW_WIDTH_MAX} {PREVIEW_HEIGHT_MAX}')

                lores_size = (lores_width, lores_height)

            self.camera_config = self.camera.create_still_configuration(sensor={'output_size': sensor_mode['size'], 'bit_depth': sensor_mode['bit_depth']},
                                                                        main={'format': main_format, 'size': main_size},
                                                                        lores={'format': lores_format, 'size': lores_size},
                                                                        raw=None, # no need,
                                                                        display=None,
                                                                        encode=None,
                                                                        transform=libcamera.Transform(vflip=True, hflip=True),
                                                                        buffer_count=4, # speed up capture_array()
                                                                        controls=controls)

            if align_configuration:
                self.camera.align_configuration(self.camera_config)
                print(self.camera_config['main'])

            self.encode_param[1] = configuration.files['jpeg_quality']

            try:

                self.camera.configure(self.camera_config)
                self.configured = True
                logger.info(f'{this_script}: Camera configured')
                logger.info(f'{this_script}: Main format {main_format}')
                logger.info(f"{this_script}: Main size ({configuration.camera['image_width']},{configuration.camera['image_height']})")
                logger.info(f'{this_script}: Lores format {lores_format}')
                logger.info(f"{this_script}: Lores size ({configuration.ai_detection['image_width']},{configuration.ai_detection['image_height']})")

            except RuntimeError as e:
                logger.error(f'{this_script}: Camera not configured')
                logger.info(f'{this_script}: ' + str(e))
                self.configured = False

            if need_to_restart:
                self.camera.start()

        else:

            print('Camera not supported')
            logger.error(f'{this_script}: Camera not supported')
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
            # if not self.started:
            self.camera.start()
            self.started = True
            logger.info(f'{this_script}: Camera started')
        except RuntimeError as e:
            logger.error(f'{this_script}: Camera not started')
            logger.error(f'{this_script}: ' + str(e))
            self.started = False

    def stop(self):

        if self.started:
            self.camera.close()
            self.started = False
            logger.info(f'{this_script}: Camera stopped')

    def capture(self, flush=True, to_jpeg=True, get_metadata=True):

        if self.started:
            if self.perf:
                s = time.perf_counter_ns()

            request = self.camera.capture_request(flush=flush)

            self.frame_data_main = request.make_array('main')

            self.frame_data_lores = cvtColor(request.make_array('lores'), COLOR_YUV420p2RGB)

            if get_metadata:
                self.metadata = request.get_metadata()
            else:
                self.metadata = None

            request.release()

            if self.perf:
                print(f'Capture {(time.perf_counter_ns() - s)/1E9}')

    def get_frame(self, stream='main'):

        if stream == 'lores':
            return self.frame_data_lores
        else:
            return self.frame_data_main

    def frame_to_jpeg(self, stream='main', crop=None):

        if self.perf:
            s = time.perf_counter_ns()

        if stream == 'lores':
            if crop:
                self.jpeg_data = imencode('.jpg', self.frame_data_lores[crop[0]:crop[1],crop[2]:crop[3],:], self.encode_param)[1].tobytes()
            else:
                self.jpeg_data = imencode('.jpg', self.frame_data_lores, self.encode_param)[1].tobytes()
        else:
            if crop:
                self.jpeg_data = imencode('.jpg', self.frame_data_main[crop[0]:crop[1],crop[2]:crop[3],:], self.encode_param)[1].tobytes()
            else:
                self.jpeg_data = imencode('.jpg', self.frame_data_main, self.encode_param)[1].tobytes()

        if self.perf:
            print(f'Frame to JPEG {(time.perf_counter_ns() - s)/1E9}')

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
            with open(jpeg_file_path, 'wb') as f:
                f.write(self.jpeg_data)

    def save_json(self, json_file_path, extra_metadata=None):

        if self.metadata:

            if extra_metadata:
                metadata = {}
                metadata.update(self.metadata)
                metadata.update(extra_metadata)
            else:
                metadata = self.metadata

            with open(json_file_path, 'w') as f:
                dump(metadata, f, indent=4, sort_keys=True, separators=(',', ': '))

    def get_controls(self, ctrls=None):

        if ctrls:

            controls = None # TODO

        else:

            controls = self.camera.camera_controls

        return controls

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

    # def set_scaler_crop(self, xywh):

        # control = {'ScalerCrop': xywh}
        # self.set_control(control)

    def get_fov_size(self, distance):

        self.fov = configuration.camera['fov']

        horizontal_size = tan(self.fov[0] * pi / 180 / 2) * distance * 2
        vertical_size = tan(self.fov[1] * pi / 180 / 2) * distance * 2

        # print(f'{horizontal_size} {vertical_size}')

        return horizontal_size, vertical_size

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

    camera = Camera(0)

    if camera.available:

        print(camera)

        camera.stop()

    else:

        print('No camera found')

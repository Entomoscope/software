import sys
import os
import pyaudio
import wave

from time import sleep

import logging
from logging.handlers import RotatingFileHandler

from subprocess import check_output, CalledProcessError

sys.path.append('..')

from globals_parameters import LOGS_DESKTOP_FOLDER, TODAY

# ~ A TESTER : pyalsaaudio

# AudioMoth-USB-Microphone-Cmd
# https://github.com/OpenAcousticDevices/AudioMoth-USB-Microphone-Cmd

# By default, Linux prevents writing to certain types of USB devices such as the AudioMoth.
# To use this application you must first navigate to /lib/udev/rules.d/ and create a new
# file (or edit the existing file) with the name 99-audiomoth.rules:

#   cd /lib/udev/rules.d/
#   sudo gedit 99-audiomoth.rules

# Then add the following text:

#   SUBSYSTEM=="usb", ATTRS{idVendor}=="16d0", ATTRS{idProduct}=="06f3", MODE="0666"

# On certain Linux distributions, you may also have to manually set the permissions for ports
# to allow the app to communicate with the AudioMoth. If you experience connection issues,
# try the following command: ?

#   sudo usermod -a -G dialout $(whoami)

# Copy executable to /usr/local/bin

#   sudo cp AudioMoth-USB-Microphone /usr/local/bin

# Using the AudioMoth USB Microphone Firmware and Hardware
# https://github.com/OpenAcousticDevices/Application-Notes/tree/master/Using_the_AudioMoth_USB_Microphone_Firmware_and_Hardware
# Audiomoth switch
# When in CUSTOM mode, all the configured settings are applied, and the red LED flashes.
# When in DEFAULT mode, only the configured sample rate and gain are applied, and the green LED flashes.

this_script = os.path.basename(__file__)[:-3]

today_log_path = os.path.join(LOGS_DESKTOP_FOLDER, TODAY)
if not os.path.exists(today_log_path):
    os.mkdir(today_log_path)

logger = logging.getLogger('entomoscope_microphone')
filename = os.path.join(today_log_path, TODAY + '_' + this_script + '.log')
file_handler = RotatingFileHandler(filename, mode="a", maxBytes=10000, backupCount=100, encoding="utf-8")
logger.addHandler(file_handler)
formatter = logging.Formatter('%(asctime)s.%(msecs)03d;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
file_handler.setFormatter(formatter)
logger.setLevel("DEBUG")

class Microphone2():

    AUDIO_FORMAT = pyaudio.paInt16
    NUMBER_OF_CHANNELS = 1
    CHUNK_SIZE = 2048

    SAMPLE_RATES = [8000, 16000, 32000, 48000, 96000, 192000, 250000, 384000]
    GAINS = ['low', 'low-medium', 'medium', 'medium-high', 'high']

    def __init__(self, sample_rate=None, gain=None):

        logger.info('***************')

        self.device_index = None
        self.audio = None
        self.stream = None
        self.available = False
        self.id = None
        self.sample_rate = None
        self.gain = None
        self.firmware = None

        self.detect_microphone()

        if self.available:

            logger.info('initializing microphone')

            if sample_rate or gain:
                self.set_settings(sample_rate, gain)

            self.read_configuration()

            self.get_firmware()

            logger.info(str(self).replace('\n', ';').replace('  ', ' ').replace('Microphone; ', ''))

            logger.info('microphone initialised')

        else:

            logger.warning('microphone not available')

    def detect_microphone(self):

        try:

            self.available = False

            cmd = ['/usr/local/bin/AudioMoth-USB-Microphone', 'list']

            output = check_output(cmd).decode('utf-8').split('\n')
            for out in output:
                if out:
                    logger.info(out)

            if output[-1] == '':
                output.pop(-1)

            if output[0].startswith('AudioMoth-USB-Microphone'):
                output.pop(0)

            if len(output) > 0:

                self.id = output[0].split()[0]

                self.available = True

                logger.info(f'audiomoth {self.id} found')

            else:

                self.available = False

                logger.error('audioMoth not found')

        except CalledProcessError as e:

            logger.error(f"wrong command : {' '.join(cmd)}")

        except BaseException as e:

            logger.error(str(e))
            self.available = False

    def start(self):

        success = False

        if self.available:

            logger.info('starting microphone')

            audimoth_found = False

            try:

                self.audio = pyaudio.PyAudio()

                sleep(2) # Utile ?

                logger.info(f'{self.audio.get_device_count()} audio devices found')

                devices_names = []

                for i in range(self.audio.get_device_count()):

                    devices_names.append(self.audio.get_device_info_by_index(i).get('name'))

                    if 'AudioMoth' in self.audio.get_device_info_by_index(i).get('name'):
                        self.device_index = i
                        audimoth_found = True

                if audimoth_found:

                    logger.info(f'audiomoth {self.id} found with audio device index {self.device_index}')

                    sleep(2) # Utile ?

                    # Create pyaudio stream
                    self.stream = self.audio.open(format=self.AUDIO_FORMAT,
                                                    input_device_index=self.device_index,
                                                    rate=self.sample_rate,
                                                    channels=self.NUMBER_OF_CHANNELS,
                                                    input=True,
                                                    frames_per_buffer=self.CHUNK_SIZE)

                    logger.info('audio stream opened')

                    logger.info('microphone started')

                    success = True

                else:

                    logger.error('audiomoth device not found')
                    logger.info(f'devices available : {devices_names}')

                    success = False

            except OSError as e:

                self.stream = None

                logger.error('audio stream not opened')
                logger.error(str(e))

                success = False

        return success

    def stop(self):

        if self.available:

            logger.info('stopping microphone')

            # Stop the stream, close it, and terminate the pyaudio instance
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                logger.info('audio stream closed')

            if self.audio:
                self.audio.terminate()
                logger.info('audio terminated')

            logger.info('microphone stopped')

    def set_settings(self, sample_rate=None, gain=None):

        if self.available:

            try:

                if sample_rate and gain:
                    if sample_rate in self.SAMPLE_RATES and gain in self.GAINS:
                        cmd = ['/usr/local/bin/AudioMoth-USB-Microphone', 'config', str(sample_rate), 'gain', str(gain), str(self.id)]
                    else:
                        logger.error(f'sample rate {sample_rate} Hz and gain {gain} not set')
                        logger.error(f'must be one of {self.SAMPLE_RATES} and one of {list(range(0, len(self.GAINS)))}')
                        cmd = None
                elif sample_rate:
                    if sample_rate in self.SAMPLE_RATES:
                        cmd = ['/usr/local/bin/AudioMoth-USB-Microphone', 'config', str(sample_rate), str(self.id)]
                    else:
                        logger.error(f'sample rate {sample_rate} Hz not set')
                        logger.error(f'must be one of {self.SAMPLE_RATES}')
                        cmd = None
                elif gain:
                    if gain in self.GAINS:
                        cmd = ['/usr/local/bin/AudioMoth-USB-Microphone', 'config', 'gain', str(gain), str(self.id)]
                    else:
                        logger.error(f'gain {gain} not set')
                        logger.error(f'must be one of {list(range(0, len(self.GAINS)))}')
                        cmd = None

                if cmd:

                    try:

                        logger.info(f"send command: {' '.join(cmd)}")

                        output = check_output(cmd).decode('utf-8').split('\n')

                        for out in output:
                            if out:
                                logger.info(out)

                        sleep(2)

                        output = check_output(['/usr/local/bin/AudioMoth-USB-Microphone', 'persist']).decode('utf-8').split('\n')
                        for out in output:
                            if out:
                                logger.info(out)

                        sleep(2)

                        if sample_rate:
                            self.sample_rate = sample_rate
                            logger.info(f'sample rate set to {sample_rate} Hz')

                        if gain:

                            self.gain = gain

                            logger.info(f'gain set to {self.GAINS[gain]}')

                    except CalledProcessError as e:

                        logger.error(f"wrong command : {' '.join(cmd)}")

            except BaseException as e:

                logger.error(str(e))

    def get_firmware(self):

        if self.available:

            try:

                cmd = ['/usr/local/bin/AudioMoth-USB-Microphone', 'firmware']

                output = check_output(cmd).decode('utf-8').split('\n')
                for out in output:
                    if out:
                        logger.info(out)

                sleep(2)

                if output[-1] == '':
                    output.pop(-1)

                if output[0].startswith('AudioMoth-USB-Microphone'):
                    output.pop(0)

                output = output[0].replace(' - ', ' ').split()

                self.firmware = output[2].replace('(', '').replace(')', '')

                logger.info(f'firmware read : {self.firmware}')

            except CalledProcessError as e:

                logger.error(f"wrong command : {' '.join(cmd)}")

            except BaseException as e:

                logger.error('firmware not read')
                logger.error(str(e))

    def read_configuration(self):

        if self.available:

            try:

                cmd = ['/usr/local/bin/AudioMoth-USB-Microphone', 'read']

                output = check_output(cmd).decode('utf-8').split('\n')
                for out in output:
                    if out:
                        logger.info(out)

                if output[-1] == '':
                    output.pop(-1)

                if output[0].startswith('AudioMoth-USB-Microphone'):
                    output.pop(0)

                output = output[0].replace(' - ', ' ').split()

                self.id = output[0]
                self.sample_rate = int(output[1])
                self.gain = int(output[3])

                logger.info(f'microphone configuration read : {self.id} - {self.sample_rate} Hz - {self.gain}')

            except CalledProcessError as e:

                logger.error(f"wrong command : {' '.join(cmd)}")

            except BaseException as e:

                logger.error('microphone configuration not read')
                logger.error(str(e))

    def save_recording(self, file_path, data):

        try:

            wavefile = wave.open(file_path, 'wb')
            wavefile.setnchannels(self.NUMBER_OF_CHANNELS)
            wavefile.setsampwidth(self.audio.get_sample_size(self.AUDIO_FORMAT))
            wavefile.setframerate(self.sample_rate)
            wavefile.writeframes(b''.join(data))
            wavefile.close()

            logger.info('recording saved to ' + file_path)

        except BaseException as e:

            logger.error(str(e))

    def __str__(self):

        s = 'Microphone\n'
        s += f'  ID: {self.id}\n'
        s += f'  Sample rate: {self.sample_rate}\n'
        s += f'  Gain: {self.gain}\n'
        s += f'  Audio format: {self.AUDIO_FORMAT}\n'
        s += f'  Number of channels: {self.NUMBER_OF_CHANNELS}\n'
        s += f'  Chunk size: {self.CHUNK_SIZE}\n'
        s += f'  Firmware: {self.firmware}\n'

        return s

if __name__ == '__main__':

    microphone = Microphone2(8000, 0)

    if microphone.available:

        print(microphone)

        microphone.start()

        if microphone.stream:
            print('Stream opened')
        else:
            print('Stream not opened')

        microphone.stop()

    else:

        print('Microphone not found')




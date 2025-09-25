import sys
import os
import pyaudio
import wave

from time import sleep

import logging

from subprocess import check_output

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

this_script = os.path.basename(__file__)[:-3]

today_log_path = os.path.join(LOGS_DESKTOP_FOLDER, TODAY)
if not os.path.exists(today_log_path):
    os.mkdir(today_log_path)

logger = logging.getLogger('entomoscope_microphone')
filename = os.path.join(today_log_path, TODAY + '_' + this_script + '.log')
file_handler = logging.FileHandler(filename, mode="a", encoding="utf-8")
logger.addHandler(file_handler)
formatter = logging.Formatter('%(asctime)s;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
file_handler.setFormatter(formatter)
logger.setLevel("DEBUG")

class Microphone2():

    AUDIO_FORMAT = pyaudio.paInt16
    NUMBER_OF_CHANNELS = 1
    CHUNK_SIZE = 2048

    def __init__(self):

        self.device_index = None

        self.audio = None

        self.stream = None

        self.available = False

        self.id = None
        self.sample_rate = None
        self.gain = None
        self.firmware = None

        self.detect_microphone()

        self.read_configuration()

        self.get_firmware()

        logger.info(str(self).replace('\n', ';').replace('  ', ' ').replace('Microphone; ', ''))

    def detect_microphone(self):

        try:

            self.available = False

            output = check_output(['AudioMoth-USB-Microphone', 'list']).decode('utf-8').split('\n')

            if output[-1] == '':
                output.pop(-1)

            if output[0].startswith('AudioMoth-USB-Microphone'):
                output.pop(0)

            if len(output) > 0:

                self.id = output[0].split()[0]

                self.available = True

            else:

                self.available = False

        except BaseException as e:

            logger.error(str(e))
            self.available = False

    def start(self):

        if self.available:

            audimoth_found = False

            try:

                self.audio = pyaudio.PyAudio()

                for i in range(self.audio.get_device_count()):

                    # logger.info(f'{i} ' + self.audio.get_device_info_by_index(i).get('name'))

                    if 'AudioMoth' in self.audio.get_device_info_by_index(i).get('name'):
                        self.device_index = i
                        audimoth_found = True
                        logger.info(f'Audiomoth device found with index {i}')
                        break

                if audimoth_found:

                    # Create pyaudio stream
                    self.stream = self.audio.open(format=self.AUDIO_FORMAT,
                                                    input_device_index=self.device_index,
                                                    rate=self.sample_rate,
                                                    channels=self.NUMBER_OF_CHANNELS,
                                                    input=True,
                                                    frames_per_buffer=self.CHUNK_SIZE)

                    logger.info('audio stream opened')

                else:

                    logger.error('Audiomoth device not found. Audio stream not opened')

            except OSError as e:

                self.stream = None

                logger.error('audio stream not opened')
                logger.error(str(e))

    def stop(self):

        if self.available:

            # Stop the stream, close it, and terminate the pyaudio instance
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                logger.info('audio stream closed')

            if self.audio:
                self.audio.terminate()

    def set_sample_rate(self, sample_rate):

        if self.available:

            try:

                output = check_output(['AudioMoth-USB-Microphone', 'config', str(sample_rate), str(self.id)])

                output = check_output(['AudioMoth-USB-Microphone', 'persist'])

                logger.info(f'sample rate set to {sample_rate} Hz')

            except BaseException as e:

                logger.error('sample rate not set')
                logger.error(str(e))

    def get_id(self):

        if self.available:

            try:

                output = check_output(['AudioMoth-USB-Microphone', 'read']).decode('utf-8').split('\n')

                self.id = output[1].split(' ')[0]

            except BaseException as e:

                logger.error('microphone ID not get')
                logger.error(str(e))

    def get_firmware(self):

        if self.available:

            try:

                output = check_output(['AudioMoth-USB-Microphone', 'firmware']).decode('utf-8').split('\n')

                if output[-1] == '':
                    output.pop(-1)

                if output[0].startswith('AudioMoth-USB-Microphone'):
                    output.pop(0)

                output = output[0].replace(' - ', ' ').split()

                self.firmware = output[2].replace('(', '').replace(')', '')

            except BaseException as e:

                logger.error('microphone ID not get')
                logger.error(str(e))

    def read_configuration(self):

        if self.available:

            try:

                output = check_output(['AudioMoth-USB-Microphone', 'read']).decode('utf-8').split('\n')

                if output[-1] == '':
                    output.pop(-1)

                if output[0].startswith('AudioMoth-USB-Microphone'):
                    output.pop(0)

                output = output[0].replace(' - ', ' ').split()

                self.id = output[0]
                self.sample_rate = int(output[1])
                self.gain = int(output[3])

            except BaseException as e:

                logger.error('microphone ID not get')
                logger.error(str(e))

    def save_recording(self, file_path, data):

        try:

            wavefile = wave.open(file_path, 'wb')
            wavefile.setnchannels(self.NUMBER_OF_CHANNELS)
            wavefile.setsampwidth(self.audio.get_sample_size(self.AUDIO_FORMAT))
            wavefile.setframerate(self.sample_rate)
            wavefile.writeframes(b''.join(data))
            wavefile.close()

            logger.info(f'recording saved to ' + file_path)

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

    microphone = Microphone2()

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




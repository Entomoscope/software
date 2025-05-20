import pyaudio
import wave

# ~ A TESTER : pyalsaaudio

class Microphone():

    def __init__(self, sample_rate=None):

        self.audio_format = pyaudio.paInt16
        self.number_of_channels = 1
        self.chunk_size = 4096

        self.device_index = None

        self.audio = pyaudio.PyAudio()

        self.default_sample_rate = None

        self.available = False

        self.detect_microphone()

        if sample_rate:
            self.sample_rate = sample_rate
        else:
            self.sample_rate = self.default_sample_rate

    def detect_microphone(self):

        for i in range(self.audio.get_device_count()):
            if 'AudioMoth' in self.audio.get_device_info_by_index(i).get('name'):
                self.device_index = i
                self.default_sample_rate = int(self.audio.get_device_info_by_index(i).get('defaultSampleRate'))
                break

        if self.device_index == None:
            self.available = False
        else:
            self.available = True

    def start(self):

        # Create pyaudio stream
        self.stream = self.audio.open(format=self.audio_format, rate=self.sample_rate, channels=self.number_of_channels, \
                                input_device_index=self.device_index, input=True, \
                                frames_per_buffer=self.chunk_size)

    def stop(self):

        # Stop the stream, close it, and terminate the pyaudio instance
        self.stream.stop_stream()
        self.stream.close()
        self.audio.terminate()

    def save_recording(self, file_path, data):

        wavefile = wave.open(file_path, 'wb')
        wavefile.setnchannels(self.number_of_channels)
        wavefile.setsampwidth(self.audio.get_sample_size(self.audio_format))
        wavefile.setframerate(self.sample_rate)
        wavefile.writeframes(b''.join(data))
        wavefile.close()
        
    def __str__(self):
            
        s = 'Microphone\n'
        s += f'  Sample rate: {self.sample_rate}\n'
        s += f'  Number of channels: {self.number_of_channels}\n'
        s += f'  Chunk size: {self.chunk_size}\n'
        
        return s

if __name__ == '__main__':

    microphone = Microphone()

    if microphone.available:
            
        print(microphone)

    else:

        print('Microphone not found')



import smbus
from time import sleep

SHT31_I2C_ADDRESS = 0x45

class SHT31():

    def __init__(self):

        self.i2c_bus = smbus.SMBus(1)

        self.model = 'SHT31'
        self.manufacturer = 'Sensirion'

        self.temperature = -99.0
        self.humidity = -99.0

        self.available = True

        self.get_temperature_humidity()

        # self.find()

    def find(self):

        try:

            # self.i2c_bus.read_byte_data(SHT31_I2C_ADDRESS, 0)
            self.i2c_bus.read_byte(SHT31_I2C_ADDRESS)

            self.available = True

        except Exception as e:

            if e.errno == 121:
                pass
            else:
                print(e)

            self.available = False

    def get_temperature_humidity(self):

        if not self.available:

            self.temperature = -99.0
            self.humidity = -99.0

        else:

            try:

                self.i2c_bus.write_i2c_block_data(SHT31_I2C_ADDRESS, 0x2C, [0x06])
                sleep(0.3)
                data = self.i2c_bus.read_i2c_block_data(SHT31_I2C_ADDRESS, 6)

                self.temperature = -45 + (175 * (data[0] * 256 + data[1]) / 65535.0)
                self.humidity = 100 * (data[3] * 256 + data[4]) / 65535.0

            except OSError as e:

                self.temperature = -99.0
                self.humidity = -99.0

        return self.temperature, self.humidity

    def __str__(self):

        s = 'Sensors\n'
        s+= '  Found: ' + ('yes' if self.available else 'no') + '\n'
        s += f'  Temperature: {self.temperature:.2f}C\n'
        s += f'  Humidity: {self.humidity:.2f}%\n'

        return s

if __name__ == '__main__':

    sht31 = SHT31()

    sht31.get_temperature_humidity()

    print(sht31)

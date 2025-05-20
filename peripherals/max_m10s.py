import serial
import time
import threading
import queue

import pigpio

from math import floor

from gpiozero import OutputDevice

GNSS_I2C_MODE = 0

start_nmea_message_found = False
end_nmea_message_found = False
nmea_message = None

ubx_preamble_one_found = False
ubx_preamble_two_found = False
start_ubx_message_found = False
end_ubx_message_found = False
num_ubx_bytes_read = 0
num_ubx_bytes_to_read = 9999
ubx_message = None

DEBUG = True

class MAXM10S():

    UBX_PREAMBLE_SYNC_CHARS = bytearray([0xB5, 0x62])

    CONFIG_LAYER_RAM = 1
    CONFIG_LAYER_BBR = 2
    CONFIG_LAYER_FLASH = 4
    CONFIG_LAYER_RAM_BBR = 3
    CONFIG_LAYER_ALL = 6

    ERROR = 0x01
    WARNING = 0x02
    NOTICE = 0x04
    TEST = 0x08
    DEBUG = 0x10
    ERROR_WARNING = ERROR | WARNING
    ERROR_WARNING_NOTICE = ERROR | WARNING | NOTICE
    ALL = ERROR | WARNING | NOTICE | TEST | DEBUG

    CFG_I2CINPROT_UBX =     {'key_id': 0x10710001, 'size': 4, 'value': 0}
    CFG_I2CINPROT_NMEA =    {'key_id': 0x10710002, 'size': 4, 'value': 0}
    CFG_I2COUTPROT_UBX =    {'key_id': 0x10720001, 'size': 4, 'value': 0}
    CFG_I2COUTPROT_NMEA =   {'key_id': 0x10720002, 'size': 4, 'value': 0}

    CFG_INFMSG_UBX_I2C =    {'key_id': 0x20920001, 'size': 4, 'value': ERROR}
    CFG_INFMSG_UBX_UART1 =  {'key_id': 0x20920002, 'size': 4, 'value': ERROR}
    CFG_INFMSG_UBX_SPI =    {'key_id': 0x20920005, 'size': 4, 'value': ERROR}
    CFG_INFMSG_NMEA_I2C =   {'key_id': 0x20920006, 'size': 4, 'value': ERROR}
    CFG_INFMSG_NMEA_UART1 = {'key_id': 0x20920007, 'size': 4, 'value': ERROR}
    CFG_INFMSG_NMEA_SPI =   {'key_id': 0x2092000A, 'size': 4, 'value': ERROR}

    CFG_MSGOUT_NMEA_ID_DTM_I2C =    {'key_id': 0x209100a6, 'size': 4, 'value': 0}
    CFG_MSGOUT_NMEA_ID_DTM_UART1 =  {'key_id': 0x209100a7, 'size': 4, 'value': 0}
    CFG_MSGOUT_NMEA_ID_GBS_I2C =    {'key_id': 0x209100dd, 'size': 4, 'value': 0}
    CFG_MSGOUT_NMEA_ID_GBS_UART1 =  {'key_id': 0x209100de, 'size': 4, 'value': 0}
    CFG_MSGOUT_NMEA_ID_GGA_I2C =    {'key_id': 0x209100ba, 'size': 4, 'value': 0}
    CFG_MSGOUT_NMEA_ID_GGA_UART1 =  {'key_id': 0x209100bb, 'size': 4, 'value': 0}
    CFG_MSGOUT_NMEA_ID_GLL_I2C =    {'key_id': 0x209100c9, 'size': 4, 'value': 0}
    CFG_MSGOUT_NMEA_ID_GLL_UART1 =  {'key_id': 0x209100ca, 'size': 4, 'value': 0}
    CFG_MSGOUT_NMEA_ID_GNS_I2C =    {'key_id': 0x209100b5, 'size': 4, 'value': 0}
    CFG_MSGOUT_NMEA_ID_GNS_UART1 =  {'key_id': 0x209100b6, 'size': 4, 'value': 0}
    CFG_MSGOUT_NMEA_ID_GRS_I2C =    {'key_id': 0x209100ce, 'size': 4, 'value': 0}
    CFG_MSGOUT_NMEA_ID_GRS_UART1 =  {'key_id': 0x209100cf, 'size': 4, 'value': 0}
    CFG_MSGOUT_NMEA_ID_GSA_I2C =    {'key_id': 0x209100bf, 'size': 4, 'value': 0}
    CFG_MSGOUT_NMEA_ID_GSA_UART1 =  {'key_id': 0x209100c0, 'size': 4, 'value': 0}
    CFG_MSGOUT_NMEA_ID_GST_I2C =    {'key_id': 0x209100d3, 'size': 4, 'value': 0}
    CFG_MSGOUT_NMEA_ID_GST_UART1 =  {'key_id': 0x209100d4, 'size': 4, 'value': 0}
    CFG_MSGOUT_NMEA_ID_GSV_I2C =    {'key_id': 0x209100c4, 'size': 4, 'value': 0}
    CFG_MSGOUT_NMEA_ID_GSV_UART1 =  {'key_id': 0x209100c5, 'size': 4, 'value': 0}
    CFG_MSGOUT_NMEA_ID_RLM_I2C =    {'key_id': 0x20910400, 'size': 4, 'value': 0}
    CFG_MSGOUT_NMEA_ID_RLM_UART1 =  {'key_id': 0x20910401, 'size': 4, 'value': 0}
    CFG_MSGOUT_NMEA_ID_RMC_I2C =    {'key_id': 0x209100ab, 'size': 4, 'value': 0}
    CFG_MSGOUT_NMEA_ID_RMC_UART1 =  {'key_id': 0x209100ac, 'size': 4, 'value': 0}
    CFG_MSGOUT_NMEA_ID_VLW_I2C =    {'key_id': 0x209100e7, 'size': 4, 'value': 0}
    CFG_MSGOUT_NMEA_ID_VLW_UART1 =  {'key_id': 0x209100e8, 'size': 4, 'value': 0}
    CFG_MSGOUT_NMEA_ID_VTG_I2C =    {'key_id': 0x209100b0, 'size': 4, 'value': 0}
    CFG_MSGOUT_NMEA_ID_VTG_UART1 =  {'key_id': 0x209100b1, 'size': 4, 'value': 0}
    CFG_MSGOUT_NMEA_ID_ZDA_I2C =    {'key_id': 0x209100d8, 'size': 4, 'value': 0}
    CFG_MSGOUT_NMEA_ID_ZDA_UART1 =  {'key_id': 0x209100d9, 'size': 4, 'value': 0}

    CFG_PM_OPERATEMODE = {'key_id': 0x20D00001, 'size': 4, 'value': 0}
    CFG_PM_EXTINTWAKEUP = {'key_id': 0x10D0000C, 'size': 4, 'value': 0}
    CFG_PM_EXTINTBACKUP = {'key_id': 0x10D0000D, 'size': 4, 'value': 0}

    NORMAL_OPERATION_MODE = 0
    ON_OFF_OPERATION_MODE = 1

    I2C_WAIT_BEFORE_READ = 0.5

    NAK = 0x00
    ACK = 0x01

    def __init__(self, i2c_bus=1, i2c_address=0x42, rst_pin=None, exi_pin=None, verbose=False):

        self.model = 'MAX-10S'
        self.manufacturer = 'U-blox'

        self.time = None
        self.longitude = None
        self.latitude = None
        
        self.nav_pvt = {'itow': 0,
                'year': 0,
                'month': 0,
                'day': 0,
                'hour': 0,
                'minute': 0,
                'second': 0,
                'valid': 0,
                'fix_type': 0,
                'num_sv': 0,
                'lon': 0,
                'lat': 0,
                'flag3': 0,
                'position_dop': 0.0,
                'raw': ''}

        self.pi = pigpio.pi()
        self.i2c_bus = i2c_bus
        self.i2c_handle = None
        self.i2c_address = i2c_address

        self.exi_pin = OutputDevice(exi_pin, active_high=True, initial_value=True) if exi_pin else exi_pin
        self.rst_pin = OutputDevice(rst_pin, active_high=True, initial_value=True) if rst_pin else rst_pin

        self.ubx_command = bytearray()
        self.ubx_command_class = 0
        self.ubx_command_id = 0
        self.ubx_command_payload_length = 0
        self.ubx_command_payload = bytearray()
        self.ubx_command_checksum = bytearray(2)

        self.ubx_response = bytearray()
        self.ubx_response_class = 0
        self.ubx_response_id = 0
        self.ubx_response_payload_length = 0
        self.ubx_response_payload = bytearray()
        self.ubx_response_checksum = bytearray(2)

        self.verbose = verbose

        self.connected = False

        self.software_version = ''
        self.hardware_version = ''

        self.rmc_data = {'utc_time': '', 'status': '', 'latitude': '', 'northsouth': '', 'longitude': '', 'eastwest': '', 'date': '', 'available': False}

    def com_start(self):

        if not self.connected:

            self.i2c_handle = self.pi.i2c_open(self.i2c_bus, self.i2c_address)

            # time.sleep(0.5)

            self.connected = True

    def com_stop(self):

        if self.connected:
            self.connected = False
            self.pi.i2c_close(self.i2c_handle)
            # self.pi.stop()

    def reset(self):

        self.hardware_reset()

    def get_data(self):

        self.get_nav_pvt()
        return self.time, self.latitude, self.longitude

    def disable(self):

        if self.exi_pin:
            self.exi_pin.off()
            if self.verbose:
                print('GNSS disable (EXI pin is low)')
        elif self.verbose:
            print('EXI pin not set')

    def enable(self):

        if self.exi_pin:
            self.exi_pin.on()
            if self.verbose:
                print('GNSS enable (EXI pin is high)')
        elif self.verbose:
            print('EXI pin not set')

    def hardware_reset(self):

        if self.rst_pin:
            self.rst_pin.off()
            time.sleep(0.005)
            self.rst_pin.on()
        elif self.verbose:
            print('RST pin not set')

    def set_inital_configuration(self):

        self.CFG_I2CINPROT_UBX['value'] = 1
        self.CFG_I2COUTPROT_UBX['value'] = 1
        self.CFG_I2CINPROT_NMEA['value'] = 0
        self.CFG_I2COUTPROT_NMEA['value'] = 0

        configuration_items = [
                            self.CFG_I2CINPROT_UBX,
                            self.CFG_I2CINPROT_NMEA,
                            self.CFG_I2COUTPROT_UBX,
                            self.CFG_I2COUTPROT_NMEA,
                            self.CFG_INFMSG_UBX_I2C,
                            self.CFG_INFMSG_UBX_UART1,
                            self.CFG_INFMSG_UBX_SPI,
                            self.CFG_INFMSG_NMEA_I2C,
                            self.CFG_INFMSG_NMEA_UART1,
                            self.CFG_INFMSG_NMEA_SPI,
                            self.CFG_MSGOUT_NMEA_ID_DTM_I2C,
                            self.CFG_MSGOUT_NMEA_ID_DTM_UART1,
                            self.CFG_MSGOUT_NMEA_ID_GBS_I2C,
                            self.CFG_MSGOUT_NMEA_ID_GBS_UART1,
                            self.CFG_MSGOUT_NMEA_ID_GGA_I2C,
                            self.CFG_MSGOUT_NMEA_ID_GGA_UART1,
                            self.CFG_MSGOUT_NMEA_ID_GLL_I2C,
                            self.CFG_MSGOUT_NMEA_ID_GLL_UART1,
                            self.CFG_MSGOUT_NMEA_ID_GNS_I2C,
                            self.CFG_MSGOUT_NMEA_ID_GNS_UART1,
                            self.CFG_MSGOUT_NMEA_ID_GRS_I2C,
                            self.CFG_MSGOUT_NMEA_ID_GRS_UART1,
                            self.CFG_MSGOUT_NMEA_ID_GSA_I2C,
                            self.CFG_MSGOUT_NMEA_ID_GSA_UART1,
                            self.CFG_MSGOUT_NMEA_ID_GST_I2C,
                            self.CFG_MSGOUT_NMEA_ID_GST_UART1,
                            self.CFG_MSGOUT_NMEA_ID_GSV_I2C,
                            self.CFG_MSGOUT_NMEA_ID_GSV_UART1,
                            self.CFG_MSGOUT_NMEA_ID_RLM_I2C,
                            self.CFG_MSGOUT_NMEA_ID_RLM_UART1,
                            self.CFG_MSGOUT_NMEA_ID_RMC_I2C,
                            self.CFG_MSGOUT_NMEA_ID_RMC_UART1,
                            self.CFG_MSGOUT_NMEA_ID_VLW_I2C,
                            self.CFG_MSGOUT_NMEA_ID_VLW_UART1,
                            self.CFG_MSGOUT_NMEA_ID_VTG_I2C,
                            self.CFG_MSGOUT_NMEA_ID_VTG_UART1,
                            self.CFG_MSGOUT_NMEA_ID_ZDA_I2C,
                            self.CFG_MSGOUT_NMEA_ID_ZDA_UART1,
                            self.CFG_PM_OPERATEMODE,
                            self.CFG_PM_EXTINTWAKEUP,
                            self.CFG_PM_EXTINTBACKUP
                            ]

        for configuration_item in configuration_items:
            if self.set_ubx_configuration_item(configuration_item) ==  self.NAK:
                print(f'Error setting {configuration_item} configuration item')

    # def get_date_time(self):

            # # self.ubx_command_class = 0x01
            # # self.ubx_command_id = 0x07
            # # self.ubx_command_payload_length = 92
            # # self.ubx_command_payload = bytearray(92)

            # # self.send_ubx_command()

        # return self.rmc_data['date'], self.rmc_data['utc_time']

    # def get_position(self):

            # # self.ubx_command_class = 0x01
            # # self.ubx_command_id = 0x07
            # # self.ubx_command_payload_length = 92
            # # self.ubx_command_payload = bytearray(92)

            # # self.send_ubx_command()

        # return self.rmc_data['latitude'], self.rmc_data['northsouth'], self.rmc_data['longitude'], self.rmc_data['eastwest']

    def get_nav_sig(self):

        self.ubx_command_class = 0x01
        self.ubx_command_id = 0x43
        self.ubx_command_payload_length = 0
        self.ubx_command_payload = bytearray()

        self.send_ubx_command()

    def get_nav_sat(self):

        self.ubx_command_class = 0x01
        self.ubx_command_id = 0x35
        self.ubx_command_payload_length = 0
        self.ubx_command_payload = bytearray()

        self.send_ubx_command()

    def get_nav_pvt(self):

        self.ubx_command_class = 0x01
        self.ubx_command_id = 0x07
        self.ubx_command_payload_length = 0
        self.ubx_command_payload = bytearray()

        try:

            if self.send_ubx_command() == self.ACK:

                # print([int(x) for x in self.ubx_response_payload])

                self.nav_pvt['itow'] = int.from_bytes(self.ubx_response_payload[0:4], 'little', signed=False)
                self.nav_pvt['year'] = int.from_bytes(self.ubx_response_payload[4:6], 'little', signed=False)
                self.nav_pvt['month'] = self.ubx_response_payload[6]
                self.nav_pvt['day'] = self.ubx_response_payload[7]
                self.nav_pvt['hour'] = self.ubx_response_payload[8]
                self.nav_pvt['minute'] = self.ubx_response_payload[9]
                self.nav_pvt['second'] = self.ubx_response_payload[10]
                self.nav_pvt['valid'] = self.ubx_response_payload[11] & 0x0F
                self.nav_pvt['fix_type'] = self.ubx_response_payload[20]
                self.nav_pvt['num_sv'] = self.ubx_response_payload[23]
                self.nav_pvt['lon'] = int.from_bytes(self.ubx_response_payload[24:28], 'little', signed=True) * 1E-7
                self.nav_pvt['lat'] = int.from_bytes(self.ubx_response_payload[28:32], 'little', signed=True) * 1E-7
                self.nav_pvt['flag3'] = int.from_bytes(self.ubx_response_payload[78:80], 'little', signed=False)
                
                # https://www.tersus-gnss.com/tech_blog/what-is-dop-in-gnss
                self.nav_pvt['position_dop'] = int.from_bytes(self.ubx_response_payload[76:78], 'little', signed=False) * 0.01
                
                self.nav_pvt['raw'] = f"{self.nav_pvt['day']:02d}/{self.nav_pvt['month']:02d}/{self.nav_pvt['year']:04d} {self.nav_pvt['hour']:02d}:{self.nav_pvt['minute']:02d}:{self.nav_pvt['second']:02d} [{ self.nav_pvt['valid'] & 0x01} {self.nav_pvt['valid'] & 0x02} {self.nav_pvt['valid'] & 0x04} {self.nav_pvt['valid'] & 0x08}] {self.nav_pvt['fix_type']} {self.nav_pvt['num_sv']} [{self.nav_pvt['lon']} {self.nav_pvt['lat']}] {self.nav_pvt['flag3'] & 0x01} {self.nav_pvt['position_dop']:.2f}"
                
                print(f"NAV PVT: {self.nav_pvt['raw']}")

                # self.longitude = lon
                # self.latitude = lat
                # self.time = [year, month, day, hour, minute, second]

        except BaseException as e:

            print('Something wrong happend')
            print(str(e))


    def set_power_management(self, operate_mode):

        # C:\Users\jerome\kDrive\jbtechlab\projets\get\monitoring-grotte\datasheets\gnss MAX-M10S\MAX-M10S_IntegrationManual_UBX-20053088.pdf
        # 3.6.2 Power save mode

        # C:\Users\jerome\kDrive\jbtechlab\projets\get\monitoring-grotte\datasheets\gnss MAX-M10S\u-blox-M10-SPG-5.10_InterfaceDescription_UBX-21035062.pdf
        # 4.9.15 CFG-PM: Configuration for receiver power management
        # CFG-PM-OPERATEMODE
        # CFG-PM-EXTINTWAKE
        # CFG_PM_EXTINTBACKUP

        if operate_mode == self.NORMAL_OPERATION_MODE:

            self.CFG_PM_OPERATEMODE['value'] = 0
            self.CFG_PM_EXTINTWAKEUP['value'] = 0
            self.CFG_PM_EXTINTBACKUP['value'] = 0

        elif operate_mode == self.ON_OFF_OPERATION_MODE:

            self.CFG_PM_OPERATEMODE['value'] = 1
            self.CFG_PM_EXTINTWAKEUP['value'] = 1
            self.CFG_PM_EXTINTBACKUP['value'] = 1

        configuration_items = [ self.CFG_PM_EXTINTWAKEUP,
                                self.CFG_PM_EXTINTBACKUP,
                                self.CFG_PM_OPERATEMODE]

        for configuration_item in configuration_items:
            if self.set_ubx_configuration_item(configuration_item) ==  self.NAK:
                print(f'Error setting {configuration_item} configuration item')

        # self.set_ubx_configuration_item(self.CFG_PM_OPERATEMODE)
        # self.set_ubx_configuration_item(self.CFG_PM_EXTINTWAKEUP)
        # self.set_ubx_configuration_item(self.CFG_PM_EXTINTBACKUP)

    def get_version(self):

        return self.software_version, self.hardware_version

    def read_version(self):

        self.ubx_command_class = 0x0A
        self.ubx_command_id = 0x04
        self.ubx_command_payload_length = 0

        self.ubx_command_payload = bytearray()

        self.send_ubx_command()

        self.software_version = self.ubx_response_payload[0:30].decode('utf-8').replace('\0', '')
        self.hardware_version = self.ubx_response_payload[30:40].decode('utf-8').replace('\0', '')

        num_groups = (int(self.ubx_response_payload_length) - 40) // 30
        groups = []

        for i in range(0, num_groups):
            groups.append(self.ubx_response_payload[40+i*30:40+(i+1)*30].decode('utf-8').replace('\0', ''))

        if self.verbose and DEBUG:
            print(f'SWVER={self.software_version}\nHDVER={self.hardware_version}')
            for i in range(0, num_groups):
                print(groups[i])

    def send_ubx_command(self):

        self.ubx_command = bytearray()

        self.ubx_command += self.UBX_PREAMBLE_SYNC_CHARS

        self.ubx_command += self.ubx_command_class.to_bytes(1, signed=False)
        self.ubx_command += self.ubx_command_id.to_bytes(1, signed=False)

        self.ubx_command += self.ubx_command_payload_length.to_bytes(2, 'little', signed=False)

        self.ubx_command += self.ubx_command_payload

        self.check_sum()

        self.ubx_command += self.ubx_command_checksum

        if self.verbose and DEBUG:
            print('UBX CMD: ', end='')
            self.print_ubx_message(self.ubx_command)

        self.pi.i2c_write_device(self.i2c_handle, self.ubx_command)

        time.sleep(self.I2C_WAIT_BEFORE_READ)

        self.ubx_response = []

        (count, data) = self.pi.i2c_read_device(self.i2c_handle, 6)

        if all([x == 255 for x in data]):
            return self.NAK

        # print(data)

        self.ubx_response.extend(data)

        payload_length = int.from_bytes(data[4:6], 'little', signed=False)

        (count, data) = self.pi.i2c_read_device(self.i2c_handle, payload_length + 2)

        if count != payload_length + 2:
            return self.NAK

        self.ubx_response.extend(data)

        self.ubx_response = bytes(self.ubx_response)

        self.parse_ubx_message(self.ubx_response)

        if self.ubx_response_class == 0x05 and self.ubx_response_id == 0x01:
            return self.NAK
        elif self.ubx_response_class == 0x05 and self.ubx_response_id == 0x00:
            return self.ACK
        else:
            return self.ACK

    def check_sum(self):

        self.ubx_command_checksum[0] = 0;
        self.ubx_command_checksum[1] = 0;

        self.ubx_command_checksum[0] = (self.ubx_command_checksum[0] + self.ubx_command_class) & 0xFF
        self.ubx_command_checksum[1] = (self.ubx_command_checksum[1] + self.ubx_command_checksum[0]) & 0xFF

        self.ubx_command_checksum[0] = (self.ubx_command_checksum[0] + self.ubx_command_id) & 0xFF
        self.ubx_command_checksum[1] = (self.ubx_command_checksum[1] + self.ubx_command_checksum[0]) & 0xFF

        self.ubx_command_checksum[0] = (self.ubx_command_checksum[0] + (self.ubx_command_payload_length & 0xFF)) & 0xFF
        self.ubx_command_checksum[1] = (self.ubx_command_checksum[1] + self.ubx_command_checksum[0]) & 0xFF

        self.ubx_command_checksum[0] = (self.ubx_command_checksum[0] + (self.ubx_command_payload_length >> 8)) & 0xFF
        self.ubx_command_checksum[1] = (self.ubx_command_checksum[1] + self.ubx_command_checksum[0]) & 0xFF

        for c in self.ubx_command_payload:
            self.ubx_command_checksum[0] = (self.ubx_command_checksum[0] + c) & 0xFF
            self.ubx_command_checksum[1] = (self.ubx_command_checksum[1] + self.ubx_command_checksum[0]) & 0xFF

    def get_ubx_configuration_item(self, item, layer=CONFIG_LAYER_RAM):

        # C:\Users\jerome\kDrive\jbtechlab\projets\get\monitoring-grotte\datasheets\gnss MAX-M10S\u-blox-M10-SPG-5.10_InterfaceDescription_UBX-21035062.pdf
        # 4 Configuration interface

        self.ubx_command_class = 0x06
        self.ubx_command_id = 0x8B
        self.ubx_command_payload_length = 4 + item['size']

        self.ubx_command_payload = bytearray(self.ubx_command_payload_length)

        self.ubx_command_payload[0:4] = [0x00, layer, 0x00, 0x00]

        self.ubx_command_payload[4] = item['key_id'] & 0xFF;
        self.ubx_command_payload[5] = (item['key_id'] >> 8) & 0xFF;
        self.ubx_command_payload[6] = (item['key_id'] >> 16) & 0xFF;
        self.ubx_command_payload[7] = (item['key_id'] >> 24) & 0xFF;

        self.send_ubx_command()

    def set_ubx_configuration_item(self, item, layer=CONFIG_LAYER_RAM_BBR):

        self.ubx_command_class = 0x06
        self.ubx_command_id = 0x8A
        self.ubx_command_payload_length = 4 + item['size'] + 1

        self.ubx_command_payload = bytearray(self.ubx_command_payload_length)

        self.ubx_command_payload[0:4] = [0x00, layer, 0x00, 0x00]

        self.ubx_command_payload[4] = item['key_id'] & 0xFF;
        self.ubx_command_payload[5] = (item['key_id'] >> 8) & 0xFF;
        self.ubx_command_payload[6] = (item['key_id'] >> 16) & 0xFF;
        self.ubx_command_payload[7] = (item['key_id'] >> 24) & 0xFF;
        self.ubx_command_payload[8] = item['value']

        self.send_ubx_command()

    def print_ubx_message(self, message):

        # TODO Cut long message to display only first bytes of the payload

        if len(message) < 5:
            print(f'Error message length too small')
            return

        payload_length = message[4] + message[5] * 256

        if payload_length > len(message):
            print(f'Error payload length > message length ({payload_length} > {len(message)})')
            return

        print('\n H    H    C    I    L    L    P', end='')

        if payload_length > 0:

            print('    P' * (payload_length-1), end='')
            print('    K    K')

        else:

            print('    K    K')

        print(f'0x{message[0]:02X} 0x{message[1]:02X} 0x{message[2]:02X} 0x{message[3]:02X} 0x{message[4]:02X} 0x{message[5]:02X}', end='')

        if payload_length > 0:

            for i in range(6, 6+payload_length):
                print(f' 0x{message[i]:02X}', end='')

            print(f' 0x{message[-2]:02X} 0x{message[-1]:02X}')

        else:

            print(f'      0x{message[6]:02X} 0x{message[7]:02X}')

    def parse_nmea_message(self, nmea_message):

        data = nmea_message.split(',')

        if nmea_message.startswith('$GNRMC'):

            self.parse_nmea_rmc(data)

    def parse_nmea_rmc(self, data):

        # https://portal.u-blox.com/s/question/0D52p00008HKCCzCAP/whats-the-coordinate-system-of-nmea-messages

        self.rmc_data['utc_time'] = data[1]
        self.rmc_data['status'] = data[2]
        if data[3]:
            degrees = floor(float(data[3]) / 100)
            minutes_dec = float(data[3]) - degrees * 100
            degrees_dec = degrees + minutes_dec / 60
            self.rmc_data['latitude'] = degrees_dec
        else:
            self.rmc_data['latitude'] = 0.0
        if data[4]:
            self.rmc_data['northsouth'] = data[4]
        else:
            self.rmc_data['northsouth'] = 'N'
        if data[5]:
            degrees = floor(float(data[5]) / 100)
            minutes_dec = float(data[5]) - degrees * 100
            degrees_dec = degrees + minutes_dec / 60
            self.rmc_data['longitude'] = degrees_dec
        else:
            self.rmc_data['longitude'] = 0.0
        if data[6]:
            self.rmc_data['eastwest'] = data[6]
        else:
            self.rmc_data['eastwest'] = 'E'
        self.rmc_data['date'] = data[9]

        self.rmc_data['available'] = self.rmc_data['longitude'] != 0.0 and self.rmc_data['latitude'] != 0.0

    def parse_ubx_message(self, ubx_message):

        self.ubx_response = ubx_message
        self.ubx_response_class = self.ubx_response[2]
        self.ubx_response_id = self.ubx_response[3]
        self.ubx_response_payload_length = int.from_bytes(self.ubx_response[4:6], 'little', signed=False)
        self.ubx_response_payload = self.ubx_response[6:-2]
        self.ubx_response_checksum = self.ubx_response[-2:]

        if self.verbose and DEBUG:
            print('UBX MSG: ', end='')
            self.print_ubx_message(self.ubx_response)

def demo():
    
    print('Start')
    
    # gnss = MAXM10S(i2c_bus=1, i2c_address=0x42, rst_pin=GNSS_RESET_PIN, exi_pin=GNSS_EXI_PIN, verbose=False)
    gnss = MAXM10S(i2c_bus=1, i2c_address=0x42, verbose=False)
    
    gnss.enable()
    
    gnss.com_start()
    
    # gnss.set_inital_configuration()
    
    gnss.read_version()
    
    # gnss.set_power_management(gnss.ON_OFF_OPERATION_MODE)
    
    # time.sleep(2)
    
    # gnss.disable()
    
    # gnss.read_version()
    
    
    # gnss.hardware_reset()
    # print('Reset')

    # gnss.start()

    # # gnss.set_inital_configuration()
    # gnss.set_power_management(gnss.ON_OFF_OPERATION_MODE)

    # # # gnss.enable()

    # # # gnss.read_version()

    # # # gnss.stop()

    # # # gnss.set_inital_configuration()

    # # # # gnss.set_power_management(gnss.ON_OFF_OPERATION_MODE)

    # # # # enable = True

    # # # # all_start_time = time.time()
    # pos_start_time = time.time()
    # # # # start_time = time.time()

    # # # # count = 0

    while True:

        try:
            
            
            # data = gnss.pi.i2c_read_byte_data(gnss.i2c_bus, 0xFF)
            
            # if data != 0xFF:    
            
                # print(data)
            
            # count = gnss.pi.i2c_read_byte_data(gnss.i2c_bus, 0xFD) * 256
            # count += gnss.pi.i2c_read_byte_data(gnss.i2c_bus, 0xFE)
            
            # # print(num)
            
            # if count > 0:
                
                # # data = gnss.pi.i2c_read_device(gnss.i2c_bus, count)
                # data = gnss.pi.i2c_read_i2c_block_data(gnss.i2c_bus, 0xFF, count)
                
                # print(data)
                
            # byte = gnss.pi.i2c_read_byte(gnss.i2c_bus)
            
            # print(byte)

            gnss.get_data()

            # # if data and len(data) > 0 and data[0] != 255:
                # # print(data)

            # if time.time() - pos_start_time > 1:

                # pos_start_time = time.time()

                # # gnss.get_nav_sig()

                # # time.sleep(0.3)

                # # gnss.get_nav_sat()

                # # time.sleep(0.3)

                # gnss.get_nav_pvt()

                # # gnss.read_version()

                # # data = gnss.read()

                # # print(data)



                # # d, t = gnss.get_date_time()
                # # lat, ns, lon, ew = gnss.get_position()

                # # count += 1

                # # print(f'{count:03d} Date: {d[0:2]}/{d[2:4]}/{d[4:]} Time: {t} Position: {lat}{ns} {lon}{ew}')

            # # # if time.time() - start_time > 10:

                # # # start_time = time.time()

                # # # if enable:
                    # # # gnss.disable()
                    # # # enable = False
                    # # # print('*** Disable ***')
                # # # else:
                    # # # gnss.enable()
                    # # # gnss.set_inital_configuration()
                    # # # enable = True
                    # # # print('*** Enable ***')

            # # if time.time() - all_start_time > 180:

                # # gnss.stop()
                # # print('Timeout')
                # # break


            # time.sleep(0.1)

        except KeyboardInterrupt:

            gnss.stop()
            print('Demo stopped by user')
            break

if __name__=='__main__':

    demo()




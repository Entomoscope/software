from subprocess import check_output
# from gpiozero import CPUTemperature

class Rpi():

    def __init__(self):

        self.model = self.get_model()
        self.revision = self.get_revision()
        self.serial = self.get_serial()
        # self.ram = self.get_ram()

        self.hostname = self.get_hostname()

        # self.cpu_temperature = CPUTemperature()
        self.cpu_temperature = self.get_temperature()

        self.wifi_ssid = self.get_wifi_ssid()

        self.ip_address = self.get_ip_address()

        self.pigpio_supported = not(self.model.startswith('Raspberry Pi 5'))
        
        self.os_version = self.get_os_version()

    def get_model(self):

        # # TODO : compare with from /proc/cpuinfo
        # with open('/proc/device-tree/model') as f:
            # model = f.read().strip('\x00')

        model = check_output('cat /proc/cpuinfo | grep "Model"', shell=True).decode('utf-8').split(':')[1].strip()

        return model

    def get_serial(self):

        serial = check_output('cat /proc/cpuinfo | grep "Serial"', shell=True).decode('utf-8').split(':')[1].strip()

        return serial

    def get_revision(self):

        revision = check_output('cat /proc/cpuinfo | grep "Revision"', shell=True).decode('utf-8').split(':')[1].strip()

        return revision

    def get_hostname(self):

        hostname = check_output('hostname', shell=True).decode('utf-8').strip()

        return hostname

    def get_wifi_ssid(self):

        # self.wifi_ssid = check_output(['iwgetid', '-r']).decode('utf-8').strip()

        try:
            # wifi_ssid = check_output('nmcli d show wlan0 | grep "GENERAL.CONNECTION:"', shell=True).decode('utf-8').split()[1].split('/')[0]
            wifi_ssid = check_output('nmcli d show wlan0 | grep "GENERAL.CONNECTION:"', shell=True).decode('utf-8').split(':')[1].strip()
        except:
            wifi_ssid = None

        return wifi_ssid

    def get_ip_address(self, version='v4'):

        try:

            if version == 'v4':
                try:
                    ip = check_output('nmcli d show wlan0 | grep "IP4.ADDRESS\[1]:"', shell=True).decode('utf-8').split()[1].split('/')[0]
                except:
                    ip = 'XXX.XXX.XXX.XXX'
            elif version == 'v6':
                try:
                    ip = check_output('nmcli d show wlan0 | grep "IP6.ADDRESS\[1]:"', shell=True).decode('utf-8').split()[1].split('/')[0]
                except:
                    ip = 'XXX.XXX.XXX.XXX'
        except:

            ip = 'XXX.XXX.XXX.XXX'

        return ip

    # def get_ram(self):

        # TODO RAM
        # https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#raspberry-pi-revision-codes
        # w = check_output(['cat', '/proc/device-tree/compatible']).decode('utf-8').strip().split('\0')
        # self.ram =
        
    def get_temperature(self):
        
        # https://github.com/gpiozero/gpiozero/blob/master/gpiozero/internal_devices.py#L215
        
        sensor_file = '/sys/class/thermal/thermal_zone0/temp'
		
        try:
            
            with open(sensor_file, 'r') as f:
                cpu_temperature = float(f.read().strip()) / 1000
                
        except BaseException as e:
            
            cpu_temperature = 0.0
            print(e)
            
        return cpu_temperature
        
    def get_os_version(self):
    
        if 'aarch64' in check_output('uname -m', shell=True).decode('utf-8').strip():
            os_version = '64-bit'
        else:
            os_version = '32-bit'

        return os_version

    def __str__(self):

        s = 'Raspberry Pi\n'
        s += '  Model: ' + self.model + '\n'
        s += '  Revision: ' + self.revision + '\n'
        s += '  Serial: ' + self.serial + '\n'
        s += '  Hostname: ' + self.hostname + '\n'
        # s += '  pigpio support: ' + 'yes\n' if self.pigpio_supported else 'no\n'
        s += '  CPU Temperature: ' + f'{self.get_temperature():.2f}' + '\n'
        s += '  WiFi: ' + self.wifi_ssid + '\n'
        s += '  IP address: ' + self.ip_address + '\n'
        s += '  OS version: ' + self.os_version + '\n'

        return s

if __name__ == '__main__':

    rpi = Rpi()

    print(rpi)


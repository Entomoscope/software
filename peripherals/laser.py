from time import time, sleep

class Laser():

    def __init__(self):


        pass


    def detect_something(self):

        return False


if __name__ == '__main__':

    print('Start laser')

    laser = Laser()

    start_time = time()

    while time() - start_time < 10:

        print(laser.detect_something())

        sleep(0.5)

    print('End laser')

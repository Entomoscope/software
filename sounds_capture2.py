import os
from time import time, sleep
from datetime import datetime, timedelta

import logging
from logging.handlers import RotatingFileHandler

import pigpio

pi = pigpio.pi()

from configuration2 import Configuration2

from peripherals.microphone2 import Microphone2
from peripherals.pinout2 import SOUNDS_CAPTURE_ACTIVITY_PIN, SHUTDOWN_PIN, STARTUP_PIN

from globals_parameters import SOUNDS_CAPTURE_FOLDER, LOGS_DESKTOP_FOLDER, TODAY, MICROPHONE_DETECTION_INTERVAL, MICROPHONE_DETECTION_NUM_TRIES, MICROPHONE_STARTUP_DELAY_BEFORE_FIST_CAPTURE

this_script = os.path.basename(__file__)[:-3]

def isStartupCompleted():

    return pi.read(STARTUP_PIN)

def isSignalToShutdownReceived():

    return pi.read(SHUTDOWN_PIN)

def isSignalToStandByReceived():

    return pi.read(SOUNDS_CAPTURE_ACTIVITY_PIN)

def main():

    today_log_path = os.path.join(LOGS_DESKTOP_FOLDER, TODAY)
    if not os.path.exists(today_log_path):
        os.mkdir(today_log_path)

    logger = logging.getLogger('entomoscope_sounds_capture2')
    filename = os.path.join(today_log_path, TODAY + '_' + this_script + '.log')
    file_handler = RotatingFileHandler(filename, mode="a", maxBytes=10000, backupCount=100, encoding="utf-8")
    logger.addHandler(file_handler)
    formatter = logging.Formatter('%(asctime)s.%(msecs)03d;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
    file_handler.setFormatter(formatter)
    logger.setLevel("DEBUG")

    logger.info('****************************')

    logger.info(f'sounds capture script started with pid {os.getpid()}')

    logger.info('wait for startup script to complete')

    # Attente du signal de démarrage complet du sytème
    # La broche STARTUP_PIN doit passer à l'état haut
    while not isStartupCompleted():
        if isSignalToShutdownReceived():
            logger.info('shutdown signal received')
            logger.info('sounds capture script stopped')
            exit()
        sleep(0.5)

    logger.info('startup script completed')

    logger.info(f'sounds capture folder: {SOUNDS_CAPTURE_FOLDER}')

    if isSignalToStandByReceived():

        logger.info('in standby mode. Wait for resume signal to start capturing sounds')

        # Tant que la broche SOUNDS_CAPTURE_ACTIVITY_PIN est à l'état haut => capture de son en pause
        while isSignalToStandByReceived():

            # Si la broche SHUTDOWN_PIN passe à l'état haut => arret capture de son
            if isSignalToShutdownReceived():
                logger.info('shutdown signal received')
                logger.info('sounds capture stopped')
                exit()

            sleep(0.5)

        # La broche SOUNDS_CAPTURE_ACTIVITY_PIN est à l'état bas, le script se poursuit
        logger.info('resume signal received')

    # Lecture du fichier de configuration
    configuration = Configuration2()
    logger.info('configuration file read')

    # Détection du micro pendant MICROPHONE_DETECTION_NUM_TRIES essais
    for i in range(0, MICROPHONE_DETECTION_NUM_TRIES):

        logger.info(f'Detecting the microphone ({i}/{MICROPHONE_DETECTION_NUM_TRIES} tries)')

        microphone = Microphone2(configuration.microphone['sample_rate'], configuration.microphone['gain'])

        # Si le micro est disponible => on poursuit le cript
        if microphone.available:
            break
        # Sinon, on attend MICROPHONE_DETECTION_INTERVAL secondes avant de refaire une détection
        else:
            start_detect_time = time()
            while (time() - start_detect_time) < MICROPHONE_DETECTION_INTERVAL:

                if isSignalToShutdownReceived():
                    logger.info('shutdown signal received')
                    logger.info('sounds capture stopped')
                    exit()

                sleep(0.5)

    # Si le micro est disponible
    if microphone.available:

        logger.info('microphone found')

        # Attente pour démarrer le micro MICROPHONE_STARTUP_DELAY_BEFORE_FIST_CAPTURE secondes avant l'heure de démarrage de la capture son fixée dans le fichier de configuration
        try:
            configuration_startup_hour = int(configuration.schedule['next_startup'][11:13])
            configuration_startup_minute = int(configuration.schedule['next_startup'][14:16])
            now = datetime.now()
            t = datetime(now.year, now.month, now.day, configuration_startup_hour, configuration_startup_minute, 0) - timedelta(seconds=MICROPHONE_STARTUP_DELAY_BEFORE_FIST_CAPTURE)
            delta = t - now
            if delta.total_seconds() > 0:
                logger.info(f'wait {delta.total_seconds()} seconds until {configuration.schedule["next_startup"][11:13]}:{configuration.schedule["next_startup"][14:16]} before starting microphone')
                while (now < t):
                    delta = t - now
                    if delta.total_seconds() > 0.1:
                        sleep(0.1)
                    else:
                        sleep(delta.total_seconds())
                    now = datetime.now()
            else:
                logger.warning(f'too late to start the microphone correctly ({-delta} seconds)')
        except BaseException as e:
            logger.error(str(e))

        # Démarrage du micro
        microphone.start()

        # Si le micro est correctement démarré
        if microphone.stream:

            logger.info(f'microphone started at sample rate {microphone.sample_rate} Hz')
            logger.info(f"sound capture duration {configuration.sounds_capture['duration']} seconds")

            shutdown_signal_received = False
            standby_signal_received = False

            on_duration = configuration.schedule['on_duration']
            off_duration = configuration.schedule['off_duration']

            logger.info(f"on duration: {configuration.schedule['on_duration']} seconds")
            logger.info(f"off duration: {configuration.schedule['off_duration']} seconds")

            # Attente pour démarrer pile à l'heure de démarrage de la capture son fixée dans le fichier de configuration
            try:
                configuration_startup_hour = int(configuration.schedule['next_startup'][11:13])
                configuration_startup_minute = int(configuration.schedule['next_startup'][14:16])
                now = datetime.now()
                t = datetime(now.year, now.month, now.day, configuration_startup_hour, configuration_startup_minute, 0)
                delta = t - now
                if delta.total_seconds() > 0:
                    logger.info(f'wait {delta.total_seconds()} seconds until {configuration.schedule["next_startup"][11:13]}:{configuration.schedule["next_startup"][14:16]} before capturing sounds')
                    while (now < t):
                        delta = t - now
                        if delta.total_seconds() > 0.1:
                            sleep(0.1)
                        else:
                            sleep(delta.total_seconds())
                        now = datetime.now()
                else:
                    logger.info(f'too late to start capture on time ({-delta} seconds)')
            except BaseException as e:
                logger.error(str(e))

            # Copie du fichier de configuration dans le dossier où les sons sont enregistrées
            # Nom du fichier : configuration_YYYYMMDDHHMMSS.json
            now_str = datetime.now().strftime('%Y%m%d%H%M%S')
            file_path = os.path.join(SOUNDS_CAPTURE_FOLDER, 'configuration_' + now_str + '.json')
            configuration.copy_to(file_path)
            logger.info(f'configuration file saved to {file_path}')

            # Forçage du système à démarrer en mode On avec capture de son immédiate
            on = True
            off = not(on)
            force_on = True

            previous_on_time = time()
            previous_off_time = time()

            data = []

            # Démarrage du code de capture de son
            logger.info('start capturing sounds')

            while True:

                try:

                    # Si capture On et période capture On terminée => capture Off
                    if on and (time() - previous_on_time > on_duration):

                        previous_off_time = time()
                        on = False
                        off = True
                        logger.info('sounds capture off')

                    # Si capture Off et période capture Off terminée, ou forçage capture On => capture On et capture de son immédiate
                    if (off and (time() - previous_off_time > off_duration)) or force_on:

                        previous_on_time = time()
                        previous_capture_time = 0
                        force_on = False
                        on = True
                        off = False
                        logger.info('sounds capture on')

                    # Si capture On
                    if on:

                        # Nom du fichier WAV : YYYYMMDDHHMMSS.wav
                        now_str = datetime.now().strftime('%Y%m%d%H%M%S')
                        file_path = os.path.join(SOUNDS_CAPTURE_FOLDER, now_str + '.wav')

                        data.clear()

                        logger.info('start recording')

                        # Nombre d'échantillons à enregistrer en fonction du taux d'échantillonage et de la durée de la capture
                        total_samples = microphone.sample_rate * configuration.sounds_capture['duration']

                        while total_samples > 0:

                            samples = min(total_samples, microphone.CHUNK_SIZE)
                            data.append(microphone.stream.read(samples, exception_on_overflow=False))
                            total_samples -= samples

                            # Si la broche SOUNDS_CAPTURE_ACTIVITY_PIN passe à l'état haut = arret enregistrement
                            if isSignalToStandByReceived():
                                standby_signal_received = True
                                logger.info('standby signal received. Sounds capture paused')
                                break

                            # Si la broche SHUTDOWN_PIN passe à l'état haut = arret enregistrement
                            if isSignalToShutdownReceived():
                                shutdown_signal_received = True
                                logger.info('shutdown signal received. Sounds capture stopped')
                                break

                        logger.info('stop recording')

                        # Enregistrement du fichier WAV
                        microphone.save_recording(file_path, data)
                        logger.info(f'recording saved to {file_path}')

                    # Si la broche SOUNDS_CAPTURE_ACTIVITY_PIN passe à l'état haut => capture de son en pause
                    if isSignalToStandByReceived() or standby_signal_received:

                        logger.info('in standby mode. Wait for signal to resume')

                        # Tant que la broche SOUNDS_CAPTURE_ACTIVITY_PIN est à l'état haut => capture de son en pause
                        while isSignalToStandByReceived():
                            # Si la broche SHUTDOWN_PIN passe à l'état haut => arret capture de son
                            if isSignalToShutdownReceived():
                                shutdown_signal_received = True
                                break
                            sleep(0.5)

                        # Si la broche SOUNDS_CAPTURE_ACTIVITY_PIN est à l'état bas => capture de son reprend
                        if not isSignalToStandByReceived():

                            logger.info('resume signal received')
                            standby_signal_received = False

                            # Lecture du fichier de configuration
                            configuration.read()
                            logger.info('configuration read')

                            # Copie du fichier de configuration dans le dossier où les images sont enregistrées
                            # Nom du fichier : configuration_YYYYMMDDHHMMSS.json
                            now_str = datetime.now().strftime('%Y%m%d%H%M%S')
                            file_path = os.path.join(SOUNDS_CAPTURE_FOLDER, 'configuration_' + now_str + '.json')
                            configuration.copy_to(file_path)
                            logger.info(f'configuration file saved to {file_path}')

                            logger.info(f"sound capture duration {configuration.sounds_capture['duration']} seconds")

                            # Configuration des périodes d'alternance On/Off de capture de son
                            on_duration = configuration.schedule['on_duration']
                            off_duration = configuration.schedule['off_duration']

                            logger.info(f"on duration: {configuration.schedule['on_duration']} seconds")
                            logger.info(f"off duration: {configuration.schedule['off_duration']} seconds")

                    # Si la broche SHUTDOWN_PIN passe à l'état haut, on arrete le script
                    if isSignalToShutdownReceived() or shutdown_signal_received:
                        logger.info('shutdown signal received')
                        break

                except BaseException as e:

                    logger.error(str(e))

                    break

                sleep(0.05)

        else:

            logger.error("can't start microphone")

        # Arret du microphone
        microphone.stop()

    else:

        logger.error('microphone not found')

    pi.write(SOUNDS_CAPTURE_ACTIVITY_PIN, 1)

    logger.info(f'sounds capture stopped')

if __name__=='__main__':

    main()

import os
from time import time, sleep
from datetime import datetime, timedelta

import logging
from logging.handlers import RotatingFileHandler

import pigpio

pi = pigpio.pi()

from configuration2 import Configuration2

from peripherals.camera2 import Camera2
from peripherals.leds import Leds
from peripherals.laser import Laser
from peripherals.pinout2 import IMAGES_CAPTURE_ACTIVITY_PIN, SHUTDOWN_PIN, STARTUP_PIN, LEDS_REAR_DEPORTED_UV_PIN, LEDS_FRONT_PIN
from peripherals.rpi import Rpi

from globals_parameters import DATA_FOLDER, AI_MODEL_PATH, AI_ENABLE, LOGS_DESKTOP_FOLDER, TODAY

this_script = os.path.basename(__file__)[:-3]

def isStartupCompleted():

    return pi.read(STARTUP_PIN)

def isSignalToShutdownReceived():

    return pi.read(SHUTDOWN_PIN)

def isSignalToStandByReceived():

    return pi.read(IMAGES_CAPTURE_ACTIVITY_PIN)

def main():

    today_log_path = os.path.join(LOGS_DESKTOP_FOLDER, TODAY)
    if not os.path.exists(today_log_path):
        os.mkdir(today_log_path)

    logger = logging.getLogger('entomoscope_images_capture2')
    filename = os.path.join(today_log_path, TODAY + '_' + this_script + '.log')
    file_handler = RotatingFileHandler(filename, mode="a", maxBytes=10000, backupCount=100, encoding="utf-8")
    logger.addHandler(file_handler)
    formatter = logging.Formatter('%(asctime)s.%(msecs)03d;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
    file_handler.setFormatter(formatter)
    logger.setLevel("DEBUG")

    logger.info('****************************')

    logger.info(f'images capture script started with pid {os.getpid()}')

    logger.info('wait for startup script to complete')

    # Attente du signal de démarrage complet du sytème
    # La broche STARTUP_PIN doit passer à l'état haut
    while not isStartupCompleted():
        if isSignalToShutdownReceived():
            logger.info('shutdown signal received')
            logger.info('images capture script stopped')
            exit()
        sleep(0.5)

    logger.info('startup script completed')

    # Vérification que le Raspberry Pi peut prendre en charge l'IA
    rpi = Rpi()

    try:

        # IA seulement disponible sur OS 64-bit
        if rpi.arch_version == '64-bit':

            if AI_ENABLE:

                AI_AVAILABLE = True
                logger.info('64-bit arch => AI available')
                start_time = datetime.now()
                from ultralytics import YOLO
                elapsed_time = datetime.now() - start_time
                logger.info(f"YOLO import time: {elapsed_time.seconds + 1} seconds")

            else:

                AI_AVAILABLE = False
                logger.info('64-bit arch => AI available but manualy disabled')

        else:
            AI_AVAILABLE = False
            logger.info('32-bit arch => AI not available')

    except BaseException as e:

        AI_AVAILABLE = False
        logger.info('Unable to manage AI => AI not available')
        logger.error(str(e))

    if isSignalToStandByReceived():

        logger.info('in standby mode. Wait for resume signal to start capturing images')

        # Tant que la broche IMAGES_CAPTURE_ACTIVITY_PIN est à l'état haut => capture d'image en pause
        while isSignalToStandByReceived():

            # Si la broche SHUTDOWN_PIN passe à l'état haut => arret capture d'image
            if isSignalToShutdownReceived():
                logger.info('shutdown signal received')
                logger.info('images capture stopped')
                exit()

            sleep(0.5)

        # La broche IMAGES_CAPTURE_ACTIVITY_PIN est à l'état bas, le script se poursuit
        logger.info('resume signal received')

    # Lecture du fichier de configuration
    configuration = Configuration2()
    logger.info('configuration file read')

    logger.info(f"capturing images using mode {configuration.mode['mode']}")
    logger.info(f"capturing images using time step of {configuration.images_capture['time_step']} seconds")

    images_capture_time_step = configuration.images_capture['time_step']
    images_capture_time_step_delta = timedelta(seconds=images_capture_time_step)

    # Paramétrage des LEDs Front
    leds_front = Leds(LEDS_FRONT_PIN)
    if configuration.mode['mode'] == 'trap' or configuration.mode['mode'] == 'lepinoc' or configuration.mode['mode'] == 'moth':
        leds_front.set_intensity(configuration.leds['intensity_front'])
        logger.info(f"LEDs front intensity set to {configuration.leds['intensity_front']} %")
    else: # Mode deported
        leds_front.turn_off()
        logger.info("LEDs front off")

    # Paramétrage des LEDs Rear/Deported/UV
    leds_rear_deported_uv = Leds(LEDS_REAR_DEPORTED_UV_PIN)
    leds_rear_deported_uv.set_intensity(configuration.leds['intensity_rear_deported_uv'])

    if configuration.mode['mode'] == 'trap':
        logger.info(f"LEDs rear intensity set to {configuration.leds['intensity_rear_deported_uv']} %")
    elif configuration.mode['mode'] == 'lepinoc':
        logger.info(f"LEDs UV intensity set to {configuration.leds['intensity_rear_deported_uv']} %")
    elif configuration.mode['mode'] == 'deported':
        logger.info(f"LEDs deported intensity set to {configuration.leds['intensity_rear_deported_uv']} %")
    elif configuration.mode['mode'] == 'moth':
        logger.info(f"LEDs UV intensity set to {configuration.leds['intensity_rear_deported_uv']} %")

    leds_delay_on = configuration.leds['delay_on']
    leds_delay_on_delta = timedelta(seconds=leds_delay_on)
    leds_delay_off = configuration.leds['delay_off']
    leds_delay_off_delta = timedelta(seconds=leds_delay_off)
    leds_always_on = configuration.leds['always_on']

    if leds_always_on:
        logger.info('LEDs always on enabled')
    else:
        logger.info(f"delay LEDs on before image capture {leds_delay_on} seconds")
        logger.info(f"delay LEDs off after image capture {leds_delay_off} seconds")

    # Configuration des périodes d'alternance On/Off de capture d'images
    on_duration = configuration.schedule['on_duration']
    logger.info(f"capture on duration: {configuration.schedule['on_duration']} seconds")
    off_duration = configuration.schedule['off_duration']
    logger.info(f"capture off duration: {configuration.schedule['off_duration']} seconds")

    on_duration_delta = timedelta(seconds=on_duration)
    off_duration_delta = timedelta(seconds=off_duration)

    # Activation de l'IA si disponible et activée dans le fichier de configuration
    if AI_AVAILABLE:

        try:

            if configuration.ai_detection['enable']:

                logger.info('AI enabled')

                if configuration.ai_detection['file']:
                    ai_model_file = os.path.join(AI_MODEL_PATH, configuration.ai_detection['file'])
                else:
                    ai_model_files = os.listdir(AI_MODEL_PATH)
                    if len(ai_model_files) > 0:
                        ai_model_file = os.path.join(AI_MODEL_PATH, ai_model_files[0])
                        logger.warning(f'no AI model file in config file')
                        logger.warning(f'use {ai_model_files[0]} by default')
                        configuration.ai_detection['file'] = ai_model_files[0]
                        configuration.save()
                    else:
                      ai_model_file = None
                      AI_AVAILABLE = False
                      logger.warning(f'no AI model file found in {AI_MODEL_PATH}')
                      logger.warning(f'AI disabled')

                if ai_model_file:

                    AI_AVAILABLE = True
                    start_time = datetime.now()
                    ai_model = YOLO(ai_model_file)
                    elapsed_time = datetime.now() - start_time
                    logger.info(f"AI model file loaded: {configuration.ai_detection['file']}")
                    logger.info(f"AI model file loading time: {elapsed_time.seconds}.{elapsed_time.microseconds} seconds")

                    logger.info(f"detection using images of size {configuration.ai_detection['image_width']}x{configuration.ai_detection['image_height']}")
                    logger.info(f"detection using minimal confidence of {configuration.ai_detection['min_confidence']}")

            else:

                logger.info('AI disabled')

        except BaseException as e:

            AI_AVAILABLE = False
            logger.info('unable to manage AI => AI not available')
            logger.error(str(e))

    # Configuration du laser
    # if configuration.laser['enable']:
    #    laser = Laser()
    # else:
    #    laser = None

    fast_image_capture_mode = configuration.images_capture['fast_mode']
    fast_mode_one_second = 1
    fast_mode_one_second_delta = timedelta(seconds=fast_mode_one_second)
    no_detection_successive_counter_max = 3
    capture_every_second_activated = False
    no_detection_successive_counter = 0

    if fast_image_capture_mode:
        logger.info('fast capture mode enable (every second if arthropod detected)')

    multifocus_mode = configuration.images_capture['multifocus']['enable']
    lens_position_offset_mm = configuration.images_capture['multifocus']['lens_position_offset']
    lens_position_offset_dioptre = configuration.images_capture['multifocus']['lens_position_offset']
    if multifocus_mode:
        logger.info('multifocus mode enable')
        logger.info(f'multifocus lens position offset {lens_position_offset_mm} mm / {lens_position_offset_dioptre} dioptre')

    # Initialisation de la caméra
    try:
        camera = Camera2(configuration=configuration, perf=True)
    except BaseException as e:
        logger.error('something bad happended with the camera')
        logger.error(str(e))
        logger.info('images capture stopped')
        exit()

    if camera.camera is None:
        logger.error('camera not found')
        logger.info('images capture stopped')
        exit()

    if not camera.configured:
        logger.error('camera not configured')
        logger.info('images capture stopped')
        exit()

    # Démarrage de la caméra
    camera.start()

    # Si capture en mode Lepinoc ou Moth => allumer les LEDs UV
    if configuration.mode['mode'] == 'lepinoc' or configuration.mode['mode'] == 'moth':
        leds_rear_deported_uv.turn_on()

    # Définition des metadata complémentaires enregistrées pour chaque capture
    extra_metadata = {'EntomoscopeSiteID': configuration.site['id'],
                        'EntomoscopeLatitude': configuration.gnss['latitude'],
                        'EntomoscopeLongitude': configuration.gnss['longitude'],
                        'EntomoscopeAltitude': configuration.gnss['altitude'],
                        'EntomoscopeLedsFrontIntensity': configuration.leds['intensity_front'],
                        'EntomoscopeLedsRearDeportedUvIntensity': configuration.leds['intensity_rear_deported_uv'],
                        'EntomoscopeLedsDelayOn': leds_delay_on,
                        'EntomoscopeLedsDelayOff': leds_delay_off,
                        'EntomoscopeAiAvailable': AI_AVAILABLE,
                        'EntomoscopeAiEnable': configuration.ai_detection['enable'],
                        'EntomoscopeAiModel': configuration.ai_detection['file'],
                        'EntomoscopeCameraModel': configuration.camera['model'],
                        'EntomoscopeFocusMode': configuration.camera['autofocus']['mode'],
                        'EntomoscopeRaspberryPiModel': rpi.model,
                        'EntomoscopeRaspberryPiMemory': rpi.memory,
                        'EntomoscopeRaspberryPiSerialNumber': rpi.serial,
                        'EntomoscopeAiPredictionNumBoxes': 0,
                        'EntomoscopeAiPredictionSpeed': 0,
                        'EntomoscopeAiPredictionBoxes': [],
                        'EntomoscopeAiPredictionLabels': [],
                        'EntomoscopeAiPredictionConf': [],
                        'EntomoscopeAiImageScale': configuration.ai_detection['image_scale'],
                        'EntomoscopeAiImageSize': [configuration.ai_detection['image_width'], configuration.ai_detection['image_height']]
                        }

    # Si IA disponible et IA activée et mode différent de Lepinoc => faire une détection pour de faux car la première prend toujours plus de temps
    if AI_AVAILABLE and configuration.ai_detection['enable'] and configuration.mode['mode'] != 'lepinoc' :

        logger.info('dummy AI detection')

        camera.capture(get_metadata=False)

        # Exécution du script IA
        prediction = ai_model.predict(camera.frame_data_lores,
                                        imgsz=(configuration.ai_detection['image_width'], configuration.ai_detection['image_height']),
                                        conf=configuration.ai_detection['min_confidence'],
                                        show=False,
                                        save=False,
                                        save_txt=False,
                                        verbose=False)[0]

    shutdown_signal_received = False

    # Attente pour démarrer la capture d'image pile à l'heure fixée dans le fichier de configuration
    try:
        configuration_startup_hour = int(configuration.schedule['next_startup'][11:13])
        configuration_startup_minute = int(configuration.schedule['next_startup'][14:16])
        now = datetime.now()
        t = datetime(now.year, now.month, now.day, configuration_startup_hour, configuration_startup_minute, 0) - timedelta(seconds=leds_delay_on)
        delta = t - now
        if delta.total_seconds() > 0:
            logger.info(f'wait {delta.total_seconds()} seconds until {configuration.schedule["next_startup"][11:13]}:{configuration.schedule["next_startup"][14:16]} before capturing images')
            while (now < t):
                delta = t - now
                if delta.total_seconds() > 0.1:
                    sleep(0.1)
                else:
                    sleep(delta.total_seconds())
                now = datetime.now()
        else:
            logger.info(f'too late to start capture on time ({-delta} seconds). Start immediately')
    except BaseException as e:
        logger.error(str(e))

    # Copie du fichier de configuration dans le dossier où les images sont enregistrées
    # Nom du fichier : configuration_YYYYMMDDHHMMSS.json
    now_str = datetime.now().strftime('%Y%m%d%H%M%S')

    data_now_folder = os.path.join(DATA_FOLDER, now_str[0:8])
    if not os.path.exists(data_now_folder):
        os.mkdir(data_now_folder)
    images_folder = os.path.join(data_now_folder, 'Images')
    if not os.path.exists(images_folder):
        os.mkdir(images_folder)

    file_path = os.path.join(images_folder, 'configuration_' + now_str + '.json')
    configuration.copy_to(file_path)
    logger.info(f'configuration file saved to {file_path}')

    # Forçage du système à démarrer en mode On avec capture d'image immédiate
    on = False
    off = not(on)
    force_on = True

    first_on = True
    first_off = True

    now = datetime.now()

    next_on = datetime(now.year, now.month, now.day, configuration_startup_hour, configuration_startup_minute, 0)
    next_off = datetime(now.year, now.month, now.day, configuration_startup_hour, configuration_startup_minute, 0)
    next_capture = datetime(now.year, now.month, now.day, configuration_startup_hour, configuration_startup_minute, 0)

    arthropod_detected = False

    # Démarrage du code de capture d'images
    logger.info('start capturing images')

    while True:

        now = datetime.now()

        # Si capture On et période capture On terminée => capture Off
        if on and now > next_off:

            next_on = next_off + off_duration_delta - leds_delay_on_delta

            on = False
            off = True
            arthropod_detected = False
            capture_every_second_activated = False

            # Extinction des LEDs en fonction du mode
            if configuration.mode['mode'] == 'trap': # Front Off et Rear Off
                leds_front.turn_off()
                leds_rear_deported_uv.turn_off()
            elif configuration.mode['mode'] == 'moth': # Front Off et UV On
                leds_front.turn_off()
                leds_rear_deported_uv.turn_on()
            elif configuration.mode['mode'] == 'lepinoc': # Front Off et UV On
                leds_front.turn_off()
                leds_rear_deported_uv.turn_on()
            elif configuration.mode['mode'] == 'deported': # Front Off et Deported Off
                leds_front.turn_off()
                leds_rear_deported_uv.turn_off()

            logger.info('images capture off')

            logger.info(f"next on {next_on.strftime('%H:%M:%S')}")

        # Si capture Off et période capture Off terminée, ou forçage capture On => capture On et capture d'image immédiate
        if (off and now > next_on) or force_on:

            if first_off:

                next_off = next_on + on_duration_delta

                first_off = False

            else:

                next_off = next_on + on_duration_delta + leds_delay_on_delta

            on = True
            off = False
            force_on = False
            arthropod_detected = False

            next_capture = now

            leds_always_on = configuration.leds['always_on']

            # Si mode LEDs toujours allumées
            if leds_always_on:

                # Allumage des LEDs en fonction du mode
                if configuration.mode['mode'] == 'trap': # Front On et Rear On
                    leds_front.turn_on()
                    leds_rear_deported_uv.turn_on()
                elif configuration.mode['mode'] == 'moth': # Front On et UV On
                    leds_front.turn_on()
                    leds_rear_deported_uv.turn_on()
                elif configuration.mode['mode'] == 'lepinoc': # Front On et UV On
                    leds_front.turn_on()
                    leds_rear_deported_uv.turn_on()
                elif configuration.mode['mode'] == 'deported': # Front Off et Deported On
                    leds_front.turn_off()
                    leds_rear_deported_uv.turn_on()

            logger.info('images capture on')

            logger.info(f"next off {next_off.strftime('%H:%M:%S')}")

        # Si On et période entre deux captures terminée => capture
        if on and ( now >= next_capture ):

            if not capture_every_second_activated:
                next_capture += images_capture_time_step_delta
            else:
                next_capture += fast_mode_one_second_delta

            # Si pas mode LEDs toujours allumées
            if not leds_always_on:

                # Gestion des LEDs avant capture d'image en fonction du mode
                if configuration.mode['mode'] == 'trap': # Front On et Rear On
                    leds_front.turn_on()
                    leds_rear_deported_uv.turn_on()
                elif configuration.mode['mode'] == 'moth': # Front On et UV Off
                    leds_front.turn_on()
                    leds_rear_deported_uv.turn_off()
                elif configuration.mode['mode'] == 'lepinoc': # Front On et UV Off
                    leds_front.turn_on()
                    leds_rear_deported_uv.turn_off()
                elif configuration.mode['mode'] == 'deported': # Front Off et Deported On
                    leds_front.turn_off()
                    leds_rear_deported_uv.turn_on()

                # Attente avant la capture d'image pour permettre à la caméra de se stabiliser
                if leds_delay_on > 0:
                    sleep(leds_delay_on)

            # Sinon si mode Moth ou Lepinoc
            elif configuration.mode['mode'] == 'moth' or configuration.mode['mode'] == 'lepinoc':

                # Extinction LEDs UV
                leds_rear_deported_uv.turn_off() # UV Off

            # Récupération date et heure courante
            now_str = datetime.now().strftime('%Y%m%d%H%M%S')

            # Capture de l'image avec metadata
            camera.capture(get_metadata=True)

            logger.info('image captured')

            # Si pas mode LEDs toujours allumées
            if not leds_always_on:

                # Attente après la capture d'image pour éviter d'éteindre avant la fin de la capture
                if leds_delay_off > 0:
                    sleep(leds_delay_off)

                # Gestion des LEDs après capture d'image en fonction du mode
                if configuration.mode['mode'] == 'trap': # Front Off et Rear Off
                    leds_front.turn_off()
                    leds_rear_deported_uv.turn_off()
                elif configuration.mode['mode'] == 'moth': # Front Off et UV On
                    leds_front.turn_off()
                    leds_rear_deported_uv.turn_on()
                elif configuration.mode['mode'] == 'lepinoc': # Front Off et UV On
                    leds_front.turn_off()
                    leds_rear_deported_uv.turn_on()
                elif configuration.mode['mode'] == 'deported': # Front Off et Deported Off
                    leds_front.turn_off()
                    leds_rear_deported_uv.turn_off()

            # Sinon si mode Moth ou Lepinoc
            elif configuration.mode['mode'] == 'moth' or configuration.mode['mode'] == 'lepinoc':

                # Allumage LEDs UV
                leds_rear_deported_uv.turn_on() # UV On

            # Création du nom du fichier de base avec la date courante
            data_now_folder = os.path.join(DATA_FOLDER, now_str[0:8])
            if not os.path.exists(data_now_folder):
                os.mkdir(data_now_folder)
            images_folder = os.path.join(data_now_folder, 'Images')
            if not os.path.exists(images_folder):
                os.mkdir(images_folder)

            file_path = os.path.join(images_folder, now_str)

            # Si IA disponible et IA activée et mode différent de Lepinoc => analyse de l'image capturée
            if AI_AVAILABLE and configuration.ai_detection['enable'] and configuration.mode['mode'] != 'lepinoc' :

                # Exécution du script IA
                prediction = ai_model.predict(camera.frame_data_lores,
                                                imgsz=(configuration.ai_detection['image_width'], configuration.ai_detection['image_height']),
                                                conf=configuration.ai_detection['min_confidence'],
                                                show=False,
                                                save=False,
                                                save_txt=False,
                                                verbose=False)[0]

                # prediction = ai_model.track(frameDetect,
                                                # imgsz=(frameDetect.shape[0], frameDetect.shape[1]),
                                                # conf=configuration.ai_detection['min_confidence'],
                                                # show=False,
                                                # save=False,
                                                # save_txt=False,
                                                # verbose=False)[0]

                # Arthropode détecté si au moins une boite dans prediction
                arthropod_detected = len(prediction.boxes) > 0

                # Si arthropode(s) détecté(s)
                if arthropod_detected is True:

                    # Vitesse de la détection en millisecondes
                    speed = prediction.speed['preprocess'] + prediction.speed['inference'] + prediction.speed['postprocess']

                    # Nombre de boites détectées
                    num_boxes = len(prediction.boxes)

                    logger.info(f'{num_boxes} arthropods detected in {speed:.0f} ms')

                    extra_metadata['EntomoscopeAiPredictionNumBoxes'] = num_boxes
                    extra_metadata['EntomoscopeAiPredictionSpeed'] = f'{speed:.0f}'

                    # Récupération dans les metadata des coordonnées et de l'indice de confiance de chaque boite
                    for box in prediction.boxes:
                        extra_metadata['EntomoscopeAiPredictionBoxes'].append(box.xywhn.tolist()[0])
                        extra_metadata['EntomoscopeAiPredictionConf'].append(box.conf.item())
                        if box.is_track:
                            extra_metadata['EntomoscopeAiPredictionLabels'].append(box.id.item())

                    # Enregistrement de l'image et des metadata
                    # Nom du fichier : YYYYMMDDHHMMSS.jpg et YYYYMMDDHHMMSS.json
                    camera.frame_to_jpeg(stream='main')
                    jpeg_file_path, json_file_path = camera.save_capture(file_path, save_metadata=True, extra_metadata=extra_metadata)

                    logger.info('detection data saved (jpeg + json)')

                    extra_metadata['EntomoscopeAiPredictionBoxes'].clear()
                    extra_metadata['EntomoscopeAiPredictionConf'].clear()
                    extra_metadata['EntomoscopeAiPredictionLabels'].clear()
                    extra_metadata['EntomoscopeAiPredictionNumBoxes'] = 0
                    extra_metadata['EntomoscopeAiPredictionSpeed'] = 0

                    # Réinitialisation du compteur de non détection à 0
                    no_detection_successive_counter = 0

                    # Si mode capture rapide et capture toutes les secondes pas encore activée => activer capture toutes les secondes
                    if fast_image_capture_mode and not capture_every_second_activated:

                        capture_every_second_activated = True
                        next_capture = next_capture - images_capture_time_step_delta + fast_mode_one_second_delta
                        logger.info('capture every second enable')
                        logger.info('no detection counter reset')

                        # Allumage des LEDs en fonction du mode
                        if configuration.mode['mode'] == 'trap': # Front On et Rear On
                            leds_front.turn_on()
                            leds_rear_deported_uv.turn_on()
                        elif configuration.mode['mode'] == 'moth': # Front On et UV On
                            leds_front.turn_on()
                            leds_rear_deported_uv.turn_on()
                        elif configuration.mode['mode'] == 'lepinoc': # Front On et UV On
                            leds_front.turn_on()
                            leds_rear_deported_uv.turn_on()
                        elif configuration.mode['mode'] == 'deported': # Front Off et Deported On
                            leds_front.turn_off()
                            leds_rear_deported_uv.turn_on()

                        leds_always_on = True

                # Si aucun arthropode détecté
                else:

                    # Si mode capture rapide et capture toutes les secondes activée
                    if fast_image_capture_mode and capture_every_second_activated:

                        # Incrément du compteur de non détection
                        no_detection_successive_counter += 1
                        logger.info(f'no detection counter {no_detection_successive_counter}/{no_detection_successive_counter_max}')

                        # Si compteur de non détection est égal au nombre max de non détection successives
                        if no_detection_successive_counter == no_detection_successive_counter_max:

                            # Désactivation de capture toutes les secondes
                            capture_every_second_activated = False
                            next_capture = next_capture + images_capture_time_step_delta - fast_mode_one_second_delta

                            logger.info(f'max number of successive no detection reached ({no_detection_successive_counter_max})')
                            logger.info('capture every second disabled')
                            logger.info(f"next capture {(next_capture+leds_delay_on_delta).strftime('%H:%M:%S')}")

                            leds_always_on = configuration.leds['always_on']

                            if not leds_always_on:

                                # Extinction des LEDs en fonction du mode
                                if configuration.mode['mode'] == 'trap': # Front Off et Rear Off
                                    leds_front.turn_off()
                                    leds_rear_deported_uv.turn_off()
                                elif configuration.mode['mode'] == 'moth': # Front Off et UV On
                                    leds_front.turn_off()
                                    leds_rear_deported_uv.turn_on()
                                elif configuration.mode['mode'] == 'lepinoc': # Front Off et UV On
                                    leds_front.turn_off()
                                    leds_rear_deported_uv.turn_on()
                                elif configuration.mode['mode'] == 'deported': # Front Off et Deported Off
                                    leds_front.turn_off()
                                    leds_rear_deported_uv.turn_off()

                    else:

                        logger.info('no arthropod detected')

            # Si laser et laser détecte quelque chose
            # elif laser and laser.detect_something():
            #
            #    # Enregistrement de l'image entière et des metadata
            #    # Nom du fichier : YYYYMMDDHHMMSS_original.jpg et YYYYMMDDHHMMSS_original.json
            #    camera.frame_to_jpeg(stream='main')
            #    jpeg_file_path, json_file_path = camera.save_capture(file_path, save_metadata=True, extra_metadata=extra_metadata)

            # Si IA indisponible ou désactivée => mode timelapse => chaque capture est enregistrée
            else:

                # Enregistrement de l'image entière
                # Nom du fichier : YYYYMMDDHHMMSS_no_ai_detection.jpg
                camera.frame_to_jpeg(stream='main')
                jpeg_file_path, json_file_path = camera.save_capture(file_path + '_timelapse_no_ai.jpg', save_metadata=True, extra_metadata=extra_metadata)

                logger.info('timelapse data saved (jpeg + json)')

            logger.info(f"next capture {(next_capture+leds_delay_on_delta).strftime('%H:%M:%S')}")

        # Si la broche IMAGES_CAPTURE_ACTIVITY_PIN passe à l'état haut => capture d'image en pause
        if isSignalToStandByReceived():

            logger.info('standby signal received.mages capture paused')
            logger.info('images capture paused')

            # Extinction des LEDs
            if configuration.mode['mode'] == 'trap' or configuration.mode['mode'] == 'lepinoc' or configuration.mode['mode'] == 'deported' or configuration.mode['mode'] == 'moth':
                leds_rear_deported_uv.turn_off()
            if configuration.mode['mode'] == 'trap' or configuration.mode['mode'] == 'lepinoc' or configuration.mode['mode'] == 'moth':
                leds_front.turn_off()

            # Tant que la broche IMAGES_CAPTURE_ACTIVITY_PIN est à l'état haut => capture d'image en pause
            while isSignalToStandByReceived():
                # Si la broche SHUTDOWN_PIN passe à l'état haut => arret capture d'image
                if isSignalToShutdownReceived():
                    shutdown_signal_received = True
                    break
                sleep(0.5)

            # Si la broche IMAGES_CAPTURE_ACTIVITY_PIN est à l'état bas => capture d'image reprend
            if not isSignalToStandByReceived():

                try:

                    logger.info('resume signal received')

                    # Lecture du fichier de configuration
                    configuration.read()
                    logger.info('configuration read')

                    # Copie du fichier de configuration dans le dossier où les images sont enregistrées
                    # Nom du fichier : configuration_YYYYMMDDHHMMSS.json
                    now_str = datetime.now().strftime('%Y%m%d%H%M%S')

                    data_now_folder = os.path.join(DATA_FOLDER, now_str[0:8])
                    if not os.path.exists(data_now_folder):
                        os.mkdir(data_now_folder)
                    images_folder = os.path.join(data_now_folder, 'Images')
                    if not os.path.exists(images_folder):
                        os.mkdir(images_folder)

                    file_path = os.path.join(images_folder, 'configuration_' + now_str + '.json')
                    configuration.copy_to(file_path)
                    logger.info(f'configuration file saved to {file_path}')

                    images_capture_time_step = configuration.images_capture['time_step']
                    logger.info(f"capturing images using time step of {configuration.images_capture['time_step']} seconds")

                    images_capture_time_step_delta = timedelta(seconds=images_capture_time_step)

                    # Paramétrage des LEDs Front
                    if configuration.mode['mode'] == 'trap' or configuration.mode['mode'] == 'lepinoc' or configuration.mode['mode'] == 'moth':
                        leds_front.set_intensity(configuration.leds['intensity_front'])
                        logger.info(f"LEDs front intensity set to {configuration.leds['intensity_front']} %")
                    else: # Mode deported
                        leds_front.turn_off()
                        logger.info("LEDs front off")

                    # Paramétrage des LEDs Rear/Deported/UV
                    leds_rear_deported_uv = Leds(LEDS_REAR_DEPORTED_UV_PIN)
                    leds_rear_deported_uv.set_intensity(configuration.leds['intensity_rear_deported_uv'])
                    if configuration.mode['mode'] == 'trap':
                        logger.info(f"LEDs rear intensity set to {configuration.leds['intensity_rear_deported_uv']} %")
                    elif configuration.mode['mode'] == 'lepinoc':
                        logger.info(f"LEDs UV intensity set to {configuration.leds['intensity_rear_deported_uv']} %")
                    elif configuration.mode['mode'] == 'deported':
                        logger.info(f"LEDs deported intensity set to {configuration.leds['intensity_rear_deported_uv']} %")
                    elif configuration.mode['mode'] == 'moth':
                        logger.info(f"LEDs UV intensity set to {configuration.leds['intensity_rear_deported_uv']} %")

                    leds_delay_on = configuration.leds['delay_on']
                    leds_delay_on_delta = timedelta(seconds=leds_delay_on)
                    leds_delay_off = configuration.leds['delay_off']
                    leds_delay_off_delta = timedelta(seconds=leds_delay_off)
                    leds_always_on = configuration.leds['always_on']

                    if leds_always_on:
                        logger.info('LEDs always on enabled')
                    else:
                        logger.info(f"delay LEDs on before image capture {leds_delay_on} seconds")
                        logger.info(f"delay LEDs off after image capture {leds_delay_off} seconds")

                    # Configuration des périodes d'alternance On/Off de capture d'images
                    on_duration = configuration.schedule['on_duration']
                    logger.info(f"capture on duration: {configuration.schedule['on_duration']} seconds")
                    off_duration = configuration.schedule['off_duration']
                    logger.info(f"capture off duration: {configuration.schedule['off_duration']} seconds")

                    on_duration_delta = timedelta(seconds=on_duration)
                    off_duration_delta = timedelta(seconds=off_duration)

                    # Définition des metadata complémentaires enregistrées pour chaque capture
                    extra_metadata = {'EntomoscopeSiteID': configuration.site['id'],
                            'EntomoscopeLatitude': configuration.gnss['latitude'],
                            'EntomoscopeLongitude': configuration.gnss['longitude'],
                            'EntomoscopeAltitude': configuration.gnss['altitude'],
                            'EntomoscopeLedsFrontIntensity': configuration.leds['intensity_front'],
                            'EntomoscopeLedsRearDeportedUvIntensity': configuration.leds['intensity_rear_deported_uv'],
                            'EntomoscopeLedsDelayOn': leds_delay_on,
                            'EntomoscopeLedsDelayOff': leds_delay_off,
                            'EntomoscopeAiAvailable': AI_AVAILABLE,
                            'EntomoscopeAiEnable': configuration.ai_detection['enable'],
                            'EntomoscopeAiModel': configuration.ai_detection['file'],
                            'EntomoscopeCameraModel': configuration.camera['model'],
                            'EntomoscopeFocusMode': configuration.camera['autofocus']['mode'],
                            'EntomoscopeRaspberryPiModel': rpi.model,
                            'EntomoscopeRaspberryPiMemory': rpi.memory,
                            'EntomoscopeRaspberryPiSerialNumber': rpi.serial,
                            'EntomoscopeAiPredictionNumBoxes': 0,
                            'EntomoscopeAiPredictionSpeed': 0,
                            'EntomoscopeAiPredictionBoxes': [],
                            'EntomoscopeAiPredictionLabels': [],
                            'EntomoscopeAiPredictionConf': [],
                            'EntomoscopeAiImageScale': configuration.ai_detection['image_scale'],
                            'EntomoscopeAiImageSize': [configuration.ai_detection['image_width'], configuration.ai_detection['image_height']]
                            }

                    # Qualité JPEG
                    camera.set_encode_parameter(configuration.files['jpeg_quality'])

                    # Activation de l'IA si disponible et activée dans le fichier de configuration
                    if AI_AVAILABLE:

                        if configuration.ai_detection['enable']:

                            logger.info('AI detection enabled')

                            ai_model_file = os.path.join(AI_MODEL_PATH, configuration.ai_detection['file'])
                            start_time = datetime.now()
                            ai_model = YOLO(ai_model_file)
                            elapsed_time = datetime.now() - start_time
                            logger.info(f"AI model file loaded: {configuration.ai_detection['file']}")
                            logger.info(f"AI model file loading time: {elapsed_time.seconds}.{elapsed_time.microseconds} seconds")

                            logger.info(f"detection using images of size {configuration.ai_detection['image_width']}x{configuration.ai_detection['image_height']}")
                            logger.info(f"detection using minimal confidence of {configuration.ai_detection['min_confidence']}")

                        else:

                            logger.info('AI detection disabled')

                    else:

                        logger.info('32-bit arch => AI not available')

                    # Forçage du système à redémarrer en mode On  avec capture immédiate
                    force_on = True

                except BaseException as e:

                    logger.error(str(e))

        # Si la broche SHUTDOWN_PIN passe à l'état haut, on arrete le script
        if isSignalToShutdownReceived() or shutdown_signal_received:
            logger.info('shutdown signal received')
            break

        sleep(0.05)

    logger.info('stop capturing images')

    # Extinction des LEDs
    leds_rear_deported_uv.turn_off()
    leds_front.turn_off()

    # Arret caméra
    camera.stop()
    camera.close()

    logger.info('images capture stopped')

if __name__=='__main__':

    main()

import os
from time import time, sleep
from datetime import datetime

import logging
from logging.handlers import RotatingFileHandler

import pigpio

pi = pigpio.pi()

from configuration2 import Configuration2

from peripherals.camera2 import Camera2
from peripherals.leds import Leds
from peripherals.laser import Laser
from peripherals.pinout2 import IMAGES_CAPTURE_ACTIVITY_PIN, SHUTDOWN_PIN, LEDS_REAR_DEPORTED_UV_PIN, LEDS_FRONT_PIN
from peripherals.rpi import Rpi

from globals_parameters import IMAGES_CAPTURE_FOLDER, AI_MODEL, LOGS_DESKTOP_FOLDER, TODAY, AI_MODEL_FILE

# Vérification que le Raspberry Pi peut prendre en charge l'IA
rpi = Rpi()
if rpi.arch_version == '64-bit':
    AI_AVAILABLE = True
    from ultralytics import YOLO
else:
    AI_AVAILABLE = False

this_script = os.path.basename(__file__)[:-3]

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
    formatter = logging.Formatter('%(asctime)s;%(levelname)s;%(filename)s;%(lineno)d;"%(message)s"', datefmt='%d/%m/%Y;%H:%M:%S')
    file_handler.setFormatter(formatter)
    logger.setLevel("DEBUG")

    logger.info('started')

    logger.info(f'images capture folder: {IMAGES_CAPTURE_FOLDER}')

    if isSignalToStandByReceived():

        logger.info('in standby mode. Wait for resume signal to start capturing images')

        # Tant que la broche IMAGES_CAPTURE_ACTIVITY_PIN est à l'état haut => capture d'image en pause
        while isSignalToStandByReceived():

            # Si la broche SHUTDOWN_PIN passe à l'état haut => arret capture d'image
            if isSignalToShutdownReceived():
                logger.info('shutdown signal received')
                logger.info('stopped')
                exit()

            sleep(0.5)

        # La broche IMAGES_CAPTURE_ACTIVITY_PIN est à l'état bas, le script se poursuit
        logger.info('resume signal received')

    # Lecture du fichier de configuration
    configuration = Configuration2()
    logger.info('configuration file read')

    logger.info(f"capturing images using mode {configuration.images_capture['mode']}")
    logger.info(f"capturing images using time step of {configuration.images_capture['time_step']} seconds")

    # Paramétrage des LEDs Front
    leds_front = Leds(LEDS_FRONT_PIN)
    if configuration.images_capture['mode'] == 'trap' or configuration.images_capture['mode'] == 'lepinoc' or configuration.images_capture['mode'] == 'moth':
        leds_front.set_intensity(configuration.leds['intensity_front'])
        logger.info(f"LEDs front intensity set to {configuration.leds['intensity_front']} %")
    else: # Mode deported
        leds_front.turn_off()
        logger.info("LEDs front off")

    # Paramétrage des LEDs Rear/DEported/UV
    leds_rear_deported_uv = Leds(LEDS_REAR_DEPORTED_UV_PIN)
    leds_rear_deported_uv.set_intensity(configuration.leds['intensity_rear_deported_uv'])

    if configuration.images_capture['mode'] == 'trap':
        logger.info(f"LEDs rear intensity set to {configuration.leds['intensity_rear_deported_uv']} %")
    elif configuration.images_capture['mode'] == 'lepinoc':
        logger.info(f"LEDs UV intensity set to {configuration.leds['intensity_rear_deported_uv']} %")
    elif configuration.images_capture['mode'] == 'deported':
        logger.info(f"LEDs deported intensity set to {configuration.leds['intensity_rear_deported_uv']} %")
    elif configuration.images_capture['mode'] == 'moth':
        logger.info(f"LEDs UV intensity set to {configuration.leds['intensity_rear_deported_uv']} %")

    logger.info(f"delay LEDs on before image capture {configuration.leds['delay_on']} seconds")
    logger.info(f"delay LEDs off after image capture {configuration.leds['delay_on']} seconds")

    # Configuration des périodes d'alternance On/Off de capture d'images
    on_duration = configuration.schedule['on_duration'] * 60
    logger.info(f"capture on duration: {configuration.schedule['on_duration']} minutes")
    off_duration = configuration.schedule['off_duration'] * 60
    logger.info(f"capture off duration: {configuration.schedule['off_duration']} minutes")

    # Activation de l'IA si disponible et activée dans le fichier de configuration
    if AI_AVAILABLE:

        if configuration.ai_detection['enable']:

            logger.info('AI detection enabled')

            ai_model = YOLO(AI_MODEL)

            logger.info(f'YOLO ai_model loaded => {AI_MODEL}')
            logger.info(f"detection using images of size {configuration.ai_detection['image_width']}x{configuration.ai_detection['image_height']}")
            logger.info(f"detection using minimal confidence of {configuration.ai_detection['min_confidence']}")

        else:

            ai_model = None
            logger.info('AI detection disabled')

    else:

        logger.info('AI not available on 32-bit system')

    # Configuration du laser
    # if configuration.laser['enable']:
    #    laser = Laser()
    # else:
    #    laser = None

    # Initialisation de la caméra
    try:
        camera = Camera2(configuration=configuration)
    except BaseException as e:
        logger.error('something bad happended with the camera')
        logger.error(str(e))
        logger.info('stopped')
        exit()

    if camera.camera is None:
        logger.error('camera not found')
        logger.info('stopped')
        exit()

    if not camera.configured:
        logger.error('camera not configured')
        logger.info('stopped')
        exit()

    # Démarrage de la caméra
    camera.start()

    # Si capture en mode Lepinoc ou Moth => allumer les LEDs UV
    if configuration.images_capture['mode'] == 'lepinoc' or configuration.images_capture['mode'] == 'moth':
        leds_rear_deported_uv.turn_on()

    # Définition des metadata complémentaires enregistrées pour chaque capture
    extra_metadata = {'EntomoscopeSiteID': configuration.site['id'],
                        'EntomoscopeLatitude': configuration.gnss['latitude'],
                        'EntomoscopeLongitude': configuration.gnss['longitude'],
                        'EntomoscopeAltitude': configuration.gnss['altitude'],
                        'EntomoscopeLedsFrontIntensity': configuration.leds['intensity_front'],
                        'EntomoscopeLedsRearDeportedUvIntensity': configuration.leds['intensity_rear_deported_uv'],
                        'EntomoscopeLedsDelayOn': configuration.leds['delay_on'],
                        'EntomoscopeLedsDelayOff': configuration.leds['delay_off'],
                        'EntomoscopeAiAvailable': AI_AVAILABLE,
                        'EntomoscopeAiEnable': configuration.ai_detection['enable'],
                        'EntomoscopeAiModel': AI_MODEL_FILE}

    # Copie du fichier de configuration dans le dossier où les images sont enregistrées
    # Nom du fichier : configuration_YYYYMMDDHHMMSS.json
    now_str = datetime.now().strftime('%Y%m%d%H%M%S')
    file_path = os.path.join(IMAGES_CAPTURE_FOLDER, 'configuration_' + now_str + '.json')
    configuration.copy_to(file_path)
    logger.info(f'configuration file saved to {file_path}')

    shutdown_signal_received = False

    # Forçage du système à démarrer en mode On avec capture d'image immédiate
    on = False
    off = True
    force_on = True
    previous_on_time = time()
    previous_off_time = time()
    previous_capture_time = 0

    # Démarrage du code de capture
    logger.info('start capturing images')

    while True:

        # Si On et période On terminée => Off
        if on and (time() - previous_on_time > on_duration):

            previous_off_time = time()
            on = False
            off = True
            logger.info('images capture off')

        # Si Off et période Off terminée, ou forçage On => On et capture d'image immédiate
        if (off and (time() - previous_off_time > off_duration)) or force_on:

            previous_on_time = time()
            previous_capture_time = 0
            on = True
            off = False
            force_on = False
            logger.info('images capture on')

        # Si On et période entre deux captures terminée => capture
        if on and (time() - previous_capture_time > configuration.images_capture['time_step']):

            previous_capture_time = time()

            # Récupération date et heure courante
            now_str = datetime.now().strftime('%Y%m%d%H%M%S')

            # Création du nom du fichier de base avec la date courante
            file_path = os.path.join(IMAGES_CAPTURE_FOLDER, now_str)

            # Gestion des LEDs avant capture d'image en fonction du mode
            if configuration.images_capture['mode'] == 'trap': # Front On et Rear On
                leds_front.turn_on()
                leds_rear_deported_uv.turn_on()
            elif configuration.images_capture['mode'] == 'moth': # Front On et UV Off
                leds_front.turn_on()
                leds_rear_deported_uv.turn_off()
            elif configuration.images_capture['mode'] == 'lepinoc': # Front On et UV Off
                leds_front.turn_on()
                leds_rear_deported_uv.turn_off()
            elif configuration.images_capture['mode'] == 'deported': # Front Off et Deported On
                leds_front.turn_off()
                leds_rear_deported_uv.turn_on()

            # Attente avant la capture d'image pour permettre à la caméra de se stabiliser
            if configuration.leds['delay_on']:
                sleep(configuration.leds['delay_on'])

            # Capture de l'image avec metadata
            camera.capture(get_metadata=True)

            # Attente après la capture d'image pour éviter d'éteindre avant la fin de la capture
            if configuration.leds['delay_off']:
                sleep(configuration.leds['delay_off'])

            # Gestion des LEDs après capture d'image en fonction du mode
            if configuration.images_capture['mode'] == 'trap': # Front Off et Rear Off
                leds_front.turn_off()
                leds_rear_deported_uv.turn_off()
            elif configuration.images_capture['mode'] == 'moth': # Front Off et UV On
                leds_front.turn_off()
                leds_rear_deported_uv.turn_on()
            elif configuration.images_capture['mode'] == 'lepinoc': # Front Off et UV On
                leds_front.turn_off()
                leds_rear_deported_uv.turn_on()
            elif configuration.images_capture['mode'] == 'deported': # Front Off et Deported Off
                leds_front.turn_off()
                leds_rear_deported_uv.turn_off()

            # Si IA disponible et IA activée et mode différent de Lepinoc => analyse de l'image capturée
            if AI_AVAILABLE and configuration.ai_detection['enable'] and configuration.images_capture['mode'] != 'lepinoc' :

                # Exécution du script IA
                prediction = ai_model.predict(camera.frame_data_lores,
                                                imgsz=(configuration.ai_detection['image_width'], configuration.ai_detection['image_height']),
                                                conf=configuration.ai_detection['min_confidence'],
                                                show=False,
                                                save=False,
                                                save_txt=False,
                                                verbose=False)[0]

                # Insecte détecté si boites dans prediction
                insect_detected = len(prediction.boxes) > 0

                if insect_detected is True:

                    # Enregistrement du fichier résultat prediction
                    # Nom du fichier YYYYMMDDHHMMSS_boxes_conf.txt
                    prediction.save_txt(file_path + '_boxes_conf.txt', save_conf=True)

                    # Enregistrement de l'image (taille détection) avec les boites de détection
                    # Nom du fichier YYYYMMDDHHMMSS_boxes_conf.jpg
                    prediction.save(file_path + '_boxes_conf.jpg')

                    # Enregistrement de l'image entière et des metadata
                    # Nom du fichier : YYYYMMDDHHMMSS_original.jpg et YYYYMMDDHHMMSS_original.json
                    camera.frame_to_jpeg(stream='main')
                    jpeg_file_path, json_file_path = camera.save_capture(file_path + '_original.jpg', save_metadata=True, extra_metadata=extra_metadata)

                    # Enregistrement de chaque boite de détection dans une image
                    # Nom du fichier : YYYYMMDDHHMMSS_box_N.jpg
                    box_num = 0;
                    for box in prediction.boxes:
                        box_lists = box.xywhn.tolist()
                        for box_list in box_lists:
                            x, y, w, h = int(box_list[0] * configuration.camera['image_width']), int(box_list[1] * configuration.camera['image_height']), int(box_list[2] * configuration.camera['image_width']), int(box_list[3] * configuration.camera['image_height'])
                            camera.frame_to_jpeg(stream='main', crop=[int(y-h/2),int(y+h/2),int(x-w/2),int(x+w/2)])
                            box_num += 1
                            camera.save_jpeg(file_path + f'_box_{box_num}.jpg')

            # Si laser et laser détecte quelque chose
            # elif laser and laser.detect_something():
            #
            #    # Enregistrement de l'image entière et des metadata
            #    # Nom du fichier : YYYYMMDDHHMMSS_original.jpg et YYYYMMDDHHMMSS_original.json
            #    camera.frame_to_jpeg(stream='main')
            #    jpeg_file_path, json_file_path = camera.save_capture(file_path + '_original.jpg', save_metadata=True, extra_metadata=extra_metadata)

            # Si IA indisponible ou désactivée => mode timelapse => chaque capture est enregistrée
            else:

                # Enregistrement de l'image entière
                # Nom du fichier : YYYYMMDDHHMMSS_no_ai_detection.jpg
                camera.frame_to_jpeg(stream='main')
                jpeg_file_path, json_file_path = camera.save_capture(file_path + '_no_ai_detection.jpg', save_metadata=True, extra_metadata=extra_metadata)

        # Si la broche IMAGES_CAPTURE_ACTIVITY_PIN passe à l'état haut => capture d'image en pause
        if isSignalToStandByReceived():

            logger.info('standby signal received. Images capture paused')

            # Extinction des LEDs
            if configuration.images_capture['mode'] == 'trap' or configuration.images_capture['mode'] == 'lepinoc' or configuration.images_capture['mode'] == 'deported' or configuration.images_capture['mode'] == 'moth':
                leds_rear_deported_uv.turn_off()
            if configuration.images_capture['mode'] == 'trap' or configuration.images_capture['mode'] == 'lepinoc' or configuration.images_capture['mode'] == 'moth':
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

                logger.info('resume signal received')

                # Lecture du fichier de configuration
                configuration.read()
                logger.info('configuration read')

                # Copie du fichier de configuration dans le dossier où les images sont enregistrées
                # Nom du fichier : configuration_YYYYMMDDHHMMSS.json
                now_str = datetime.now().strftime('%Y%m%d%H%M%S')
                file_path = os.path.join(IMAGES_CAPTURE_FOLDER, 'configuration_' + now_str + '.json')
                configuration.copy_to(file_path)
                logger.info(f'configuration file saved to {file_path}')

                # Paramétrage des LEDs Front
                if configuration.images_capture['mode'] == 'trap' or configuration.images_capture['mode'] == 'lepinoc' or configuration.images_capture['mode'] == 'moth':
                    leds_front.set_intensity(configuration.leds['intensity_front'])
                    logger.info(f"LEDs front intensity set to {configuration.leds['intensity_front']} %")
                else: # Mode deported
                    leds_front.turn_off()
                    logger.info("LEDs front off")

                # Paramétrage des LEDs Rear/Deported/UV
                leds_rear_deported_uv = Leds(LEDS_REAR_DEPORTED_UV_PIN)
                leds_rear_deported_uv.set_intensity(configuration.leds['intensity_rear_deported_uv'])
                if configuration.images_capture['mode'] == 'trap':
                    logger.info(f"LEDs rear intensity set to {configuration.leds['intensity_rear_deported_uv']} %")
                elif configuration.images_capture['mode'] == 'lepinoc':
                    logger.info(f"LEDs UV intensity set to {configuration.leds['intensity_rear_deported_uv']} %")
                elif configuration.images_capture['mode'] == 'deported':
                    logger.info(f"LEDs deported intensity set to {configuration.leds['intensity_rear_deported_uv']} %")
                elif configuration.images_capture['mode'] == 'moth':
                    logger.info(f"LEDs UV intensity set to {configuration.leds['intensity_rear_deported_uv']} %")

                # Définition des metadata complémentaires enregistrées pour chaque capture
                extra_metadata = {'EntomoscopeSiteID': configuration.site['id'],
                                'EntomoscopeLatitude': configuration.gnss['latitude'],
                                'EntomoscopeLongitude': configuration.gnss['longitude'],
                                'EntomoscopeAltitude': configuration.gnss['altitude'],
                                'EntomoscopeLedsFrontIntensity': configuration.leds['intensity_front'],
                                'EntomoscopeLedsRearDeportedUvIntensity': configuration.leds['intensity_rear_deported_uv'],
                                'EntomoscopeLedsDelayOn': configuration.leds['delay_on'],
                                'EntomoscopeLedsDelayOff': configuration.leds['delay_off'],
                                'EntomoscopeAiAvailable': AI_AVAILABLE,
                                'EntomoscopeAiEnable': configuration.ai_detection['enable'],
                                'EntomoscopeAiModel': AI_MODEL_FILE}

                logger.info(f"delay LEDs on before image capture {configuration.leds['delay_on']} seconds")
                logger.info(f"delay LEDs off after image capture {configuration.leds['delay_on']} seconds")

                # Configuration des périodes d'alternance On/Off de capture d'images
                on_duration = configuration.schedule['on_duration'] * 60
                logger.info(f"on duration: {configuration.schedule['on_duration']} minutes")
                off_duration = configuration.schedule['off_duration'] * 60
                logger.info(f"off duration: {configuration.schedule['off_duration']} minutes")

                # Activation de l'IA si disponible et activée dans le fichier de configuration
                if AI_AVAILABLE and configuration.ai_detection['enable']:

                    logger.info('AI detection enabled')

                    if ai_model is None:
                        ai_model = YOLO(AI_MODEL) # load .pt file

                        logger.info(f'YOLO ai_model loaded => {AI_MODEL}')
                        logger.info(f"detection using images of size {configuration.ai_detection['image_width']}x{configuration.ai_detection['image_height']}")
                        logger.info(f"detection using minimal confidence of {configuration.ai_detection['min_confidence']}")

                else:

                    ai_model = None
                    logger.info('AI detection disabled')

                # Forçage du système à redémarrer en mode On  avec capture immédiate
                force_on = True

        # Si la broche SHUTDOWN_PIN passe à l'état haut, on arrete le script
        if isSignalToShutdownReceived() or shutdown_signal_received:
            logger.info('shutdown signal received')
            break

        sleep(0.1)

    logger.info('stop capturing images')

    # Extinction des LEDs
    leds_rear_deported_uv.turn_off()
    leds_front.turn_off()

    # Arret caméra
    camera.stop()

    logger.info('stopped')

if __name__=='__main__':

    main()

#!/usr/bin/env python
import logging
import logging.config
import logging.handlers
import os

import serial

##############################################################################
# Hier muss der wait_for_shutdowntimer eingestellt werden - dieser wartet mit
# dem Herunterfahren des Raspberry Pi, fuer den Fall dass die primaere
# Stromquelle wiederhergesttelt werden sollte Dieser Timer muss kleiner sein,
# als der im StromPi3 eingestellte shutdown-timer, damit sicher
# heruntergefahren wird.

# Here you have to set the wait_for_shutdowntimer in seconds - it waits with the
# shutdown of the Raspberry pi, in the case the primary voltage source turns
# back on. This timer have to be set lower than the configured shutdown-timer
# in the StromPi3 to make a safe shutdown.

##############################################################################
WAIT_FOR_SHUTDOWNTIMER = 10
##############################################################################

LOGLEVEL = logging.DEBUG
logcfg = {
    "version": 1,
    "formatters": {
        "normal": {
            "format": "%(asctime)-15s %(levelname)-8s %(module)-14s %(message)s"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "normal",
            "level": LOGLEVEL,
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {"": {"handlers": ["console"], "level": LOGLEVEL}},
}

logging.config.dictConfig(logcfg)
logger = logging.getLogger(__name__)

T = 0  # Temporary time-variable

ser = serial.Serial(
    port="/dev/serial0",
    baudrate=38400,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1,
)

while 1:
    line = ser.readline()
    message = line.decode(encoding="UTF-8", errors="strict")
    if message:
        logger.info(message)
    if message.find("xxx--StromPiPowerBack--xxx\n") != -1:
        logger.info("PowerBack - Raspberry Pi Shutdown aborted")
        T = 0
    elif message.find("xxxShutdownRaspberryPixxx\n") != -1:
        logger.info("PowerFail - Raspberry Pi Shutdown")
        T = WAIT_FOR_SHUTDOWNTIMER + 1
    if T:
        T = T - 1
        if T:
            os.system("sudo shutdown -h now")

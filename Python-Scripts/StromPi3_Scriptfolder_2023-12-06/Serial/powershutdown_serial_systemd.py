#!/usr/bin/env python
import logging
import logging.config
import logging.handlers
import os
import signal
from threading import Thread, Timer
from time import sleep

import serial

##############################################################################
# Here you have to set the SHUTDOWN_TIMER in seconds - it waits with the
# shutdown of the Raspberry pi, in the case the primary voltage source turns
# back on. This timer have to be set lower than the configured shutdown-timer
# in the StromPi3 to make a safe shutdown.
##############################################################################
SHUTDOWN_TIMER = 10
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


class ShutdownSerial:
    """Watch the serial interface ser to signal power failure.

    If a power failure is detected, a 'Timer' is started. When this timer
    elapses, the system will be shut down, but if the power supply comes
    back, the timer will be cancelled and nothing happens.
    """

    def __init__(self, timeout):
        """Initialize.

        Parameters:
            pin: The pin where the StromPi 3 announces the power failure.
            timeout: How long to wait before initiating a system shutdown.
            mode: The GPIO mode how the pins are named.
            bounce: The bounce time (in ms).
        """
        self.timeout = timeout
        self.timers = []
        self.ser = serial.Serial()
        self.listener_thread = Thread(target=self.listen, daemon=True)

    def __del__(self):
        """Clean up behind us."""
        self.stop()

    def start(self):
        """Start watching the StromPi 3."""
        self.ser.port = "/dev/serial0"
        self.ser.baudrate = 38400
        self.ser.parity = serial.PARITY_NONE
        self.ser.stopbits = serial.STOPBITS_ONE
        self.ser.bytesize = serial.EIGHTBITS
        self.ser.timeout = 1
        while not self.ser.is_open:
            try:
                self.ser.open()
            except Exception as exc:
                logger.warning(exc)
            sleep(0.1)
        self.listener_thread.start()
        logger.info("Listening on %s", self.ser.port)

    def listen(self):
        """Listening for incomming messages"""
        while self.ser.is_open:
            if self.ser.inWaiting():
                try:
                    raw_msg = self.ser.readline()
                    message = raw_msg.decode(encoding="UTF-8", errors="strict")
                    if message and (not message.isspace()):
                        logger.info(message)
                    if message.find("xxx--StromPiPowerBack--xxx\n") != -1:
                        self.power_change(power_on=True)
                    elif message.find("xxxShutdownRaspberryPixxx\n") != -1:
                        self.power_change(power_on=False)
                except UnicodeDecodeError as exc:
                    logger.warning(exc)
                    logger.info(raw_msg)
            sleep(0.1)

    def stop(self):
        """Stop watching the StromPi 3."""
        self.ser.close()

    def signal(self, sig, _frame):
        """Handle the signal 'sig'."""
        self.stop()
        if sig == signal.SIGINT:
            logger.info("Keyboard interrupt by CTRL-C")
        logger.info("Safe shutdown in the case of power failure disabled")

    def power_change(self, power_on):
        """Callback function when the power supply changed."""
        if power_on:
            logger.info("Power back detected")
            for timer in self.timers:
                timer.cancel()
        else:
            logger.info("Power failure detected")
            timer = Timer(self.timeout, self.shutdown)
            timer.start()
            self.timers.append(timer)

    def shutdown(self):
        """Safely shut down the system."""
        logger.info("Shutdown system")
        os.system("sudo shutdown -h now")


if __name__ == "__main__":
    s = ShutdownSerial(SHUTDOWN_TIMER)
    signal.signal(signal.SIGTERM, s.signal)  # 'kill'
    signal.signal(signal.SIGINT, s.signal)  # CTRL-C
    s.start()
    print("(CTRL-C for exit)")
    signal.pause()

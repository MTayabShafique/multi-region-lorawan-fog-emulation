import logging
import os
import serial

from sensors.meta.data import Measurement
from sensors.meta.sensor import AbstractSensor


logger = logging.LoggerAdapter(logging.getLogger("sensiot"), {"class": os.path.basename(__file__)})

class ASH2200(AbstractSensor):

    def __init__(self, name, usb_serial, event, queue):
        super(ASH2200, self).__init__(name, "", event, queue)
        self.type = "ASH2200"
        self.usb_serial = usb_serial
        logger.info("{} initialized successfully".format(self.name))

    def read(self):
        measurements = []
        logger.info("Waiting for data from usb...")
        data = self.usb_serial.read()
        if data:
            converted_data = self.convert(data)
            for measurement in converted_data:
                measurements.append(measurement)
        return measurements

    def convert(self, string):
        data = []
        splitted = string.split(';')
        for id in range(1, 9):
            temp = splitted[(id + 2)].replace(",", ".")
            hum = splitted[(id + 10)].replace(",", ".")
            if temp and hum:
                measurement = Measurement(id, self.type)
                measurement.add("temperature", temp, "°C")
                measurement.add("humidity", hum, "°C")
                data.append(measurement)
        logger.info("Data converted: {}".format([e for e in data]))
        return data


class USBSerial:

    def __init__(self, config):
        self.port = config['device']
        self.baudrate = config['baudrate']
        self.timeout = config['timeout']

    def read(self):
        try:
            with serial.Serial(port=self.port,
                               baudrate=self.baudrate,
                               timeout=self.timeout) as usb:
                logger.info("Connected to {}: waiting...".format(self.port))
                data = usb.readline().decode().strip()
                if data:
                    logger.info("Data received: {}".format(data))
                    return data
        except serial.SerialException as e:
            raise

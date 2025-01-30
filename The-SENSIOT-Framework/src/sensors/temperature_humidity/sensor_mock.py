import logging
import os
import random

from sensors.meta.data import Measurement
from sensors.meta.sensor import AbstractSensor

logger = logging.LoggerAdapter(logging.getLogger("sensiot"), {"class": os.path.basename(__file__)})

class SensorMock(AbstractSensor):

    def __init__(self, name, event, queue, config):
        super(SensorMock, self).__init__(name, config, event, queue)
        self.sensor_count = config['sensor_count']
        self.temp = config['temperature']
        self.hum = config['humidity']
        self.interval = config['interval']
        self.message_counter = 0
        logger.info("{} initialized successfully".format(self.name))

    def read(self):
        self.event.wait(self.interval)
        measurements = []
        for sensor_id in range(1, self.sensor_count + 1):
            temp_derivation = random.randint(-2, 2)
            hum_derivation = random.randint(-5, 5)
            measurement = Measurement(sensor_id, "SensorMock")
            measurement.add("temperature", (self.temp + temp_derivation), "°C")
            measurement.add("humidity", (self.hum + hum_derivation), "°C")
            measurements.append(measurement)
            self.message_counter += 1
        return measurements
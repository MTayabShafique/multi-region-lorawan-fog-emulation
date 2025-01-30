import os
import logging
import json
import threading

from abc import ABCMeta, abstractmethod

logger = logging.LoggerAdapter(logging.getLogger("sensiot"), {"class": os.path.basename(__file__)})

class AbstractSensor(threading.Thread):

    __metaclass__ = ABCMeta

    def __init__(self, name, config, event, queue):
        super(AbstractSensor, self).__init__()
        self.name = name
        self.config = config
        self.event = event
        self.queue = queue
        logger.info("{} initialized successfully".format(self.name))

    def run(self):
        logger.info("Started: {}".format(self.name))
        while not self.event.is_set():
            try:
                logger.info("Reading data...")
                measurements = self.read()
                if measurements:
                    for measurement in measurements:
                        logger.info("Data received: {}".format(measurement))
                        self.queue.put(json.dumps(measurement.to_json()))
                    logger.info("Data put into queue")
            except Exception:
                raise
        logger.info("Stopped: {}".format(self.name))

    @abstractmethod
    def read(self):
        """
        Reads sensor data and returns a list of measurements
        (see sensors.meta.data.Measurements)
        """

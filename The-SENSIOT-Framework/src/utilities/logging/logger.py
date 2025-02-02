import logging


class LoggerFactory:

    def __init__(self, config):
        self.config = config
        self.level = {
            "info": logging.INFO,
            "debug": logging.DEBUG,
            "error": logging.ERROR
        }

    def create_logger(self):
        logger = logging.getLogger("sensiot")
        logger.propagate = False
        logger.setLevel(self.level[self.config['level'].lower()])

        handlers = []
        if self.config["handlers"]["streamhandler"]["enabled"]:
            handlers.append(self.__get_stream_handler())
        if self.config["handlers"]["graylog"]["enabled"]:
            handlers.append(self.__get_graylog_handler(self.config["handlers"]["graylog"]))

        handlers = self.__set_formatter(handlers, self.config['format'], self.config['dateformat'])
        logger = self.__add_handlers(logger, handlers)
        return logger

    def __get_stream_handler(self):
        return logging.StreamHandler()

    def __get_graylog_handler(self, config):
        handler = None
        host = config["host"]
        port = config["port"]
        if config["type"].lower() == "udp":
            from pygelf import GelfUdpHandler
            handler = GelfUdpHandler(host=host, port=port, include_extra_fields=True)
        elif config["type"].lower() == "tcp":
            from pygelf import GelfTcpHandler
            handler = GelfTcpHandler(host=host, port=port, include_extra_fields=True)
        elif config["type"].lower() == "http":
            from pygelf import GelfHttpHandler
            handler = GelfHttpHandler(host=host, port=port, include_extra_fields=True)
        return handler

    def __set_formatter(self, handlers, format, dateformat):
        formatter = logging.Formatter(format, datefmt=dateformat)
        for handler in handlers:
            handler.setFormatter(formatter)
        return handlers

    def __add_handlers(self, logger, handlers):
        for handler in handlers:
            logger.addHandler(handler)
        return logger

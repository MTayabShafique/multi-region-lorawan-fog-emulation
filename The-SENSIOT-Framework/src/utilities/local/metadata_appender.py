class MetaDataAppender(threading.Thread):
    def __convert(self, data):
        # Assuming `devEUI` comes from the data
        devEUI = data.get('devEUI', 'unspecified')
        return SensorData(devEUI, data)

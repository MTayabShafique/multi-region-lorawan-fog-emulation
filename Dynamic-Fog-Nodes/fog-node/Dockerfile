# Use a lightweight Python image
FROM python:3.9-slim

WORKDIR /app

# Copy the fog node application
COPY fog_node_mqtt.py .

RUN pip install --no-cache-dir paho-mqtt
#RUN apt-get update && apt-get install -y mosquitto mosquitto-clients

CMD ["python", "fog_node_mqtt.py"]

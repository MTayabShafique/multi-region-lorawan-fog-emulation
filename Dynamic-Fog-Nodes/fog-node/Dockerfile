# Use a lightweight Python image
FROM python:3.9-slim

WORKDIR /app

# Install ping (iputils-ping) along with your dependencies
RUN apt-get update && apt-get install -y iputils-ping

# Copy the fog node application file and the entire data_processors directory
COPY fog_node_mqtt.py .
COPY data_processors/ ./data_processors/

# Install dependencies
RUN pip install --no-cache-dir paho-mqtt

# Ensure the Python module path includes /app
ENV PYTHONPATH="/app"

# Set the entrypoint for the container
CMD ["python", "fog_node_mqtt.py"]

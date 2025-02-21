# Use a lightweight Python image
FROM python:3.9-slim

WORKDIR /app

# Copy the fog node application files
COPY fog_node_mqtt.py .
COPY data_processor.py .

# Install dependencies
RUN pip install --no-cache-dir paho-mqtt

# Ensure the Python module path includes /app
ENV PYTHONPATH="/app"

# Set the entrypoint for the container
CMD ["python", "fog_node_mqtt.py"]

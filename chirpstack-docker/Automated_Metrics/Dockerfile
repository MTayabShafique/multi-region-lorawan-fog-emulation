# syntax=docker/dockerfile:1

FROM python:3.9-slim

# Create a working directory inside the container
WORKDIR /app

# Copy requirements first to leverage Docker caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the Python scripts
COPY . .

# Expose nothing by default (no inbound port needed for a subscriber)
# EXPOSE  ...

# By default, run the MQTT subscriber
CMD ["python", "mqtt_subscriber.py"]

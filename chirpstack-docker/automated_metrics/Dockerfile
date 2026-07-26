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

RUN groupadd --gid 10001 sensiot && \
    useradd --uid 10001 --gid sensiot --no-create-home --shell /usr/sbin/nologin sensiot && \
    chown -R sensiot:sensiot /app

# Expose nothing by default (no inbound port needed for a subscriber)
# EXPOSE  ...

USER 10001:10001

# By default, run the MQTT subscriber
CMD ["python", "mqtt_subscriber.py"]

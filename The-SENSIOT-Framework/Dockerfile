# Base image for SensIoT
FROM alpine:latest

# Set environment variables for the virtual environment
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Set the working directory inside the container
WORKDIR /app

# Copy requirements.txt to the container
COPY requirements.txt /app/requirements.txt

# Install required dependencies and Python packages
RUN apk add -U --no-cache python3 py3-pip py3-gevent py3-flask py3-paho-mqtt py3-certifi && \
    apk add -U --virtual build-dependencies python3-dev gcc linux-headers musl-dev file && \
    python3 -m venv $VIRTUAL_ENV && \
    $VIRTUAL_ENV/bin/pip install --no-cache-dir -r requirements.txt && \
    apk del build-dependencies

# Copy the application source code to the container
COPY src /app/

# Make the main script executable
RUN chmod +x /app/manager.py

# Set the entry point for the container
ENTRYPOINT ["/app/manager.py"]

# Add metadata labels
LABEL maintainer="Tayyab" \
      version="1.0.0" \
      description="Dockerfile for the SensIoT application."

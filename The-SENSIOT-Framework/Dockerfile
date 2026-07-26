# Pin Python so native dependencies continue to receive compatible wheels.
FROM python:3.12-alpine

# Set environment variables for the virtual environment
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Set the working directory inside the container
WORKDIR /app

# Copy requirements.txt to the container
COPY requirements.txt /app/requirements.txt

# Install required dependencies and Python packages
RUN apk add --no-cache --virtual build-dependencies gcc linux-headers musl-dev && \
    python3 -m venv $VIRTUAL_ENV && \
    $VIRTUAL_ENV/bin/pip install --no-cache-dir -r requirements.txt && \
    apk del build-dependencies

# Copy the application source code to the container
COPY src /app/

# Make the main script executable
RUN chmod +x /app/manager.py

RUN addgroup -g 10001 sensiot && \
    adduser -D -H -u 10001 -G sensiot sensiot && \
    chown -R sensiot:sensiot /app /opt/venv

USER 10001:10001

# Set the entry point for the container
ENTRYPOINT ["/app/manager.py"]

# Add metadata labels
LABEL maintainer="Tayyab" \
      version="1.0.0" \
      description="Dockerfile for the SensIoT application."

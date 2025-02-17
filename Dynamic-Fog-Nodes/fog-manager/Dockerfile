FROM python:3.9-slim-buster

# Get exact host docker group ID
ARG DOCKER_GID=984
RUN groupadd -g ${DOCKER_GID} docker && \
    useradd -u 1000 -g docker -d /app appuser && \
    mkdir -p /app && chown -R appuser:docker /app

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY main.py .

# Set PYTHONPATH so that /app is in sys.path.
ENV PYTHONPATH=/app

USER appuser

CMD ["python", "-u", "main.py"]
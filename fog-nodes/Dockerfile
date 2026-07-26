FROM python:3.10-slim

WORKDIR /app

# Copy dependency files and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

RUN groupadd --gid 10001 sensiot && \
    useradd --uid 10001 --gid sensiot --no-create-home --shell /usr/sbin/nologin sensiot && \
    chown -R sensiot:sensiot /app

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/metrics', timeout=2)"

USER 10001:10001

CMD ["python", "main.py"]

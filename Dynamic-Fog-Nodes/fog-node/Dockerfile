# Use a lightweight Python image
FROM python:3.9-slim

WORKDIR /app

# Copy the fog node application
COPY fog_node.py .

# Install Flask (for exposing an API endpoint for demonstration)
RUN pip install --no-cache-dir flask

# Expose port (if the fog node exposes an API)
EXPOSE 5000

CMD ["python", "fog_node.py"]

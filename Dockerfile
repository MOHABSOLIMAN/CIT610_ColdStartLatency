# Base Layer: OS and runtime
FROM python:3.9-slim AS base
WORKDIR /app
# Use a regional Debian mirror and retry apt-get update
RUN echo "deb http://ftp.us.debian.org/debian bookworm main" > /etc/apt/sources.list && \
    echo "deb http://ftp.us.debian.org/debian-security bookworm-security main" >> /etc/apt/sources.list && \
    for i in 1 2 3; do apt-get update && break || sleep 5; done && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Function Layer: Dependencies
FROM base AS function
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instance Layer: Application code
FROM function
COPY app.py .
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
# Security: Run as non-root user
RUN useradd -m appuser
USER appuser
# Expose port
EXPOSE 5000
# Command to run the app
CMD ["flask", "run", "--host=0.0.0.0"]
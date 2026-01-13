FROM kalilinux/kali-rolling:latest

# Set non-interactive mode
ENV DEBIAN_FRONTEND=noninteractive

# Update and install base packages
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y \
    tor \
    obfs4proxy \
    python3 \
    python3-pip \
    python3-venv \
    net-tools \
    iptables \
    openssl \
    libssl-dev \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create Tor directories
RUN mkdir -p /var/lib/tor/venomous_service && \
    chown -R debian-tor:debian-tor /var/lib/tor/venomous_service && \
    chmod 700 /var/lib/tor/venomous_service

# Configure Tor
COPY config/torrc_template /etc/tor/torrc

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash venomous && \
    chown -R venomous:venomous /app

USER venomous

# Expose Tor ports
EXPOSE 9050 9051 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import socket; s = socket.socket(); s.settimeout(5); \
    s.connect(('127.0.0.1', 9050)); s.close(); print('Tor is running')"

# Start command
CMD ["sh", "-c", "tor & python3 main.py --mode server --stealth-level 3"]
#!/bin/bash
# VENOMOUS Installation Script
# For Kali Linux and Debian-based systems

set -e

echo "[*] Starting VENOMOUS installation..."
echo "[*] This script requires root privileges"

# Check if root
if [ "$EUID" -ne 0 ]; then 
    echo "[!] Please run as root"
    exit 1
fi

# Update system
echo "[*] Updating system packages..."
apt-get update
apt-get upgrade -y

# Install Tor
echo "[*] Installing Tor..."
apt-get install -y tor obfs4proxy

# Install Python dependencies
echo "[*] Installing Python dependencies..."
apt-get install -y python3-pip python3-venv python3-dev
apt-get install -y build-essential libssl-dev libffi-dev

# Install system dependencies
echo "[*] Installing system dependencies..."
apt-get install -y net-tools iptables iproute2
apt-get install -y openssl libssl-dev
apt-get install -y pkg-config libpcap-dev

# Create virtual environment
echo "[*] Creating Python virtual environment..."
python3 -m venv /opt/venomous/venv
source /opt/venomous/venv/bin/activate

# Install Python packages
echo "[*] Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# Create directory structure
echo "[*] Creating directory structure..."
mkdir -p /opt/venomous/{src,config,logs,data}
mkdir -p /var/lib/tor/venomous_service
chmod 700 /var/lib/tor/venomous_service

# Copy files
echo "[*] Copying application files..."
cp -r src/* /opt/venomous/src/
cp -r config/* /opt/venomous/config/
cp main.py /opt/venomous/
cp setup.py /opt/venomous/

# Install as system service
echo "[*] Creating system service..."
cat > /etc/systemd/system/venomous.service << EOF
[Unit]
Description=VENOMOUS Anonymous Communication System
After=network.target tor.service
Wants=tor.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/venomous
Environment=PATH=/opt/venomous/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/opt/venomous/venv/bin/python /opt/venomous/main.py --mode server --stealth-level 3
Restart=always
RestartSec=10
KillSignal=SIGTERM

# Security
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths=/var/lib/tor/venomous_service /opt/venomous/logs
ProtectHome=yes

[Install]
WantedBy=multi-user.target
EOF

# Setup Tor configuration
echo "[*] Configuring Tor..."
cat >> /etc/tor/torrc << EOF

# VENOMOUS Configuration
Log notice file /var/log/tor/venomous.log
SafeLogging 1
DataDirectory /var/lib/tor
HiddenServiceDir /var/lib/tor/venomous_service
HiddenServicePort 80 127.0.0.1:8080
SocksPort 9050
ControlPort 9051
CookieAuthentication 1
EOF

# Set permissions
echo "[*] Setting permissions..."
chown -R root:root /opt/venomous
chmod -R 700 /opt/venomous
chmod 600 /etc/systemd/system/venomous.service

# Enable and start services
echo "[*] Enabling services..."
systemctl daemon-reload
systemctl enable tor
systemctl enable venomous

# Create firewall rules
echo "[*] Configuring firewall..."
iptables -F
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT DROP
iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT -p tcp --dport 9050 -j ACCEPT
iptables -A OUTPUT -p tcp --dport 9051 -j ACCEPT

# Create uninstall script
echo "[*] Creating uninstall script..."
cat > /opt/venomous/uninstall.sh << 'UNINSTALL_EOF'
#!/bin/bash
set -e
echo "[*] Stopping VENOMOUS..."
systemctl stop venomous
systemctl disable venomous
rm -f /etc/systemd/system/venomous.service
echo "[*] Removing files..."
rm -rf /opt/venomous
echo "[*] Cleaning Tor configuration..."
sed -i '/# VENOMOUS Configuration/,+14d' /etc/tor/torrc
echo "[*] Reloading systemd..."
systemctl daemon-reload
systemctl restart tor
echo "[*] VENOMOUS uninstalled successfully"
UNINSTALL_EOF

chmod +x /opt/venomous/uninstall.sh

echo "[+] Installation complete!"
echo "[+] Start VENOMOUS with: systemctl start venomous"
echo "[+] Check status: systemctl status venomous"
echo "[+] View logs: journalctl -u venomous -f"
echo "[+] Uninstall with: /opt/venomous/uninstall.sh"
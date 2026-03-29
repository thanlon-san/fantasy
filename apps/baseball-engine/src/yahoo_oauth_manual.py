"""
Manual OAuth 2.0 implementation for Yahoo Fantasy API
Bypasses the broken yahoo-oauth library
"""

import requests
import json
import webbrowser
import ssl
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import tempfile
import os
from shared.logger import get_logger

logger = get_logger(__name__)


class OAuth2CallbackHandler(BaseHTTPRequestHandler):
    """HTTP server handler to catch the OAuth callback"""
    
    auth_code = None
    
    def do_GET(self):
        """Handle the OAuth callback GET request"""
        print(f"\n🔔 Received callback: {self.path}")
        
        # Parse the authorization code from the URL
        query = urlparse(self.path).query
        params = parse_qs(query)
        
        print(f"Query parameters: {params}")
        
        if 'code' in params:
            OAuth2CallbackHandler.auth_code = params['code'][0]
            print(f"✅ Authorization code captured!")
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"""
                <html>
                <body>
                <h1>Authorization successful!</h1>
                <p>You can close this window and return to the terminal.</p>
                </body>
                </html>
            """)
        else:
            print(f"❌ No code in parameters: {params}")
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"""
                <html>
                <body>
                <h1>Authorization failed</h1>
                <p>No authorization code received.</p>
                </body>
                </html>
            """)
    
    def log_message(self, format, *args):
        """Suppress logging messages"""
        pass


class YahooOAuth2:
    """Manual OAuth 2.0 implementation for Yahoo"""
    
    AUTH_URL = "https://api.login.yahoo.com/oauth2/request_auth"
    TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
    REDIRECT_URI = "https://localhost:8000"
    
    def __init__(self, consumer_key: str, consumer_secret: str):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.access_token = None
        self.refresh_token = None
        self.token_type = None
    
    def get_authorization_url(self) -> str:
        """Generate the authorization URL"""
        params = {
            'client_id': self.consumer_key,
            'redirect_uri': self.REDIRECT_URI,
            'response_type': 'code',
            'language': 'en-us'
        }
        
        url = self.AUTH_URL + '?'
        url += '&'.join([f"{k}={v}" for k, v in params.items()])
        return url
    
    def start_callback_server(self, port: int = 8000) -> str:
        """
        Start a local HTTPS server to catch the OAuth callback
        Returns the authorization code
        """
        OAuth2CallbackHandler.auth_code = None
        
        print(f"\n🌐 Starting HTTPS callback server on port {port}...")
        server = HTTPServer(('localhost', port), OAuth2CallbackHandler)
        
        # Create SSL context with self-signed certificate
        # This is safe for localhost OAuth callbacks
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        # Generate a temporary self-signed certificate
        print("🔒 Generating self-signed certificate...")
        cert_file, key_file = self._generate_self_signed_cert()
        context.load_cert_chain(cert_file, key_file)
        
        # Wrap the socket with SSL
        server.socket = context.wrap_socket(server.socket, server_side=True)
        print("✅ HTTPS server ready and listening...")
        
        # Run server in a separate thread
        server_thread = threading.Thread(target=server.handle_request)
        server_thread.daemon = True
        server_thread.start()
        
        # Wait for the auth code
        logger.info("Waiting for authorization...")
        print("⏳ Waiting for Yahoo to redirect back (up to 2 minutes)...\n")
        server_thread.join(timeout=120)  # Wait up to 2 minutes
        
        server.server_close()
        
        # Clean up certificate files
        try:
            os.unlink(cert_file)
            os.unlink(key_file)
        except:
            pass
        
        return OAuth2CallbackHandler.auth_code
    
    def _generate_self_signed_cert(self):
        """Generate a temporary self-signed certificate for localhost"""
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        import datetime
        
        # Generate private key
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Generate certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Local"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, u"Localhost"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Fantasy Keeper"),
            x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
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
            datetime.datetime.utcnow() + datetime.timedelta(days=1)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(u"localhost"),
            ]),
            critical=False,
        ).sign(key, hashes.SHA256())
        
        # Write to temporary files
        cert_fd, cert_file = tempfile.mkstemp(suffix='.pem')
        key_fd, key_file = tempfile.mkstemp(suffix='.key')
        
        with os.fdopen(cert_fd, 'wb') as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        with os.fdopen(key_fd, 'wb') as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        return cert_file, key_file
    
    def authorize(self) -> bool:
        """
        Complete OAuth 2.0 authorization flow
        Returns True if successful
        """
        try:
            # Generate authorization URL
            auth_url = self.get_authorization_url()
            
            print("\n" + "="*80)
            print("YAHOO AUTHORIZATION")
            print("="*80)
            print("\nOpening your browser for authorization...")
            print(f"If it doesn't open automatically, visit:")
            print(f"\n{auth_url}\n")
            
            # Open browser
            webbrowser.open(auth_url)
            
            # Wait for user to paste the code from the redirect URL
            print("\n" + "-"*80)
            print("After authorizing, Yahoo will redirect you to https://localhost:8000")
            print("Your browser will show an error (this is expected).")
            print("Look at the URL in your browser's address bar.")
            print("It will look like: https://localhost:8000/?code=XXXXXX")
            print("\nCopy the ENTIRE URL and paste it below:")
            print("-"*80)
            
            redirect_url = input("\nPaste the full redirect URL: ").strip()
            
            if not redirect_url:
                logger.error("No URL provided")
                return False
            
            # Extract code from URL
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(redirect_url)
            params = parse_qs(parsed.query)
            
            if 'code' not in params:
                logger.error(f"No authorization code found in URL: {redirect_url}")
                return False
            
            auth_code = params['code'][0]
            print(f"\n✅ Authorization code extracted: {auth_code[:10]}...")
            
            # Exchange code for access token
            return self.exchange_code_for_token(auth_code)
            
        except Exception as e:
            logger.error(f"Authorization failed: {e}")
            return False
    
    def exchange_code_for_token(self, auth_code: str) -> bool:
        """Exchange authorization code for access token"""
        try:
            data = {
                'client_id': self.consumer_key,
                'client_secret': self.consumer_secret,
                'redirect_uri': self.REDIRECT_URI,
                'code': auth_code,
                'grant_type': 'authorization_code'
            }
            
            response = requests.post(self.TOKEN_URL, data=data)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                self.refresh_token = token_data.get('refresh_token')
                self.token_type = token_data.get('token_type', 'bearer')
                
                logger.info("✅ Access token obtained successfully!")
                return True
            else:
                logger.error(f"Token exchange failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Token exchange error: {e}")
            return False
    
    def refresh_access_token(self) -> bool:
        """Refresh the access token using the refresh token"""
        if not self.refresh_token:
            logger.error("No refresh token available")
            return False
        
        try:
            data = {
                'client_id': self.consumer_key,
                'client_secret': self.consumer_secret,
                'refresh_token': self.refresh_token,
                'grant_type': 'refresh_token'
            }
            
            response = requests.post(self.TOKEN_URL, data=data)
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                # Refresh token might be updated
                if 'refresh_token' in token_data:
                    self.refresh_token = token_data['refresh_token']
                
                logger.info("✅ Access token refreshed!")
                return True
            else:
                logger.error(f"Token refresh failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return False
    
    def get_session(self) -> requests.Session:
        """Get a requests session with proper auth headers"""
        session = requests.Session()
        session.headers.update({
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        })
        return session
    
    def make_request(self, url: str, method: str = 'GET', **kwargs):
        """
        Make an authenticated request to Yahoo API
        
        Args:
            url: API endpoint URL
            method: HTTP method (GET, POST, etc.)
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            Parsed JSON response
        """
        session = self.get_session()
        
        # Add format=json if not already in URL
        if 'format=json' not in url:
            separator = '&' if '?' in url else '?'
            url = f"{url}{separator}format=json"
        
        try:
            response = session.request(method, url, **kwargs)
            response.raise_for_status()
            
            data = response.json()
            
            # Yahoo wraps everything in 'fantasy_content'
            if 'fantasy_content' in data:
                return data['fantasy_content']
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None
    
    def save_to_file(self, filepath: str):
        """Save tokens to file"""
        data = {
            'consumer_key': self.consumer_key,
            'consumer_secret': self.consumer_secret,
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'token_type': self.token_type
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Tokens saved to {filepath}")
    
    @classmethod
    def load_from_file(cls, filepath: str):
        """Load tokens from file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        oauth = cls(data['consumer_key'], data['consumer_secret'])
        oauth.access_token = data.get('access_token')
        oauth.refresh_token = data.get('refresh_token')
        oauth.token_type = data.get('token_type', 'bearer')
        
        return oauth

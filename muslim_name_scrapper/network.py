#!/usr/bin/env python3
"""
Network module for HTTP operations and session management
"""

import requests
import logging
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from .config import get_config


class NetworkManager:
    """Handles HTTP requests and session management"""
    
    def __init__(self, max_workers=None, max_retries=None, backoff_factor=None):
        # Load configuration
        self.config = get_config()
        
        # Use config values as defaults, allow override via parameters
        self.max_workers = max_workers or self.config.get('scraper.max_workers')
        self.max_retries = max_retries or self.config.get('network.retry.total')
        self.backoff_factor = backoff_factor or self.config.get('network.retry.backoff_factor')
        
        self.logger = logging.getLogger(__name__)
        self.session = self._create_session()
    
    def _create_session(self):
        """Create a robust session with connection pooling and retry strategy"""
        session = requests.Session()
        
        # Configure retry strategy with config values
        retry_config = self.config.get_section('network.retry')
        
        try:
            retry_strategy = Retry(
                total=self.max_retries,
                backoff_factor=self.backoff_factor,
                status_forcelist=retry_config.get('status_forcelist', [429, 500, 502, 503, 504]),
                allowed_methods=retry_config.get('allowed_methods', ["HEAD", "GET", "OPTIONS"])
            )
        except TypeError:
            # Fall back to old parameter name for older urllib3 versions
            retry_strategy = Retry(
                total=self.max_retries,
                backoff_factor=self.backoff_factor,
                status_forcelist=retry_config.get('status_forcelist', [429, 500, 502, 503, 504]),
                method_whitelist=retry_config.get('method_whitelist', ["HEAD", "GET", "OPTIONS"])
            )
        
        # Configure adapter with connection pooling using config values
        max_connections = self.config.get('network.max_connections', 32)
        max_size_multiplier = self.config.get('network.max_size_multiplier', 2)
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=max_connections,
            pool_maxsize=max_connections * max_size_multiplier
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set headers from configuration
        headers_config = self.config.get_section('network.headers')
        session.headers.update({
            'User-Agent': headers_config.get('user_agent', 'Mozilla/5.0 (compatible; Muslim Names Scraper)'),
            'Accept': headers_config.get('accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'),
            'Accept-Language': headers_config.get('accept_language', 'en-US,en;q=0.5'),
            'Accept-Encoding': headers_config.get('accept_encoding', 'gzip, deflate'),
            'Connection': headers_config.get('connection', 'keep-alive'),
            'Upgrade-Insecure-Requests': headers_config.get('upgrade_insecure_requests', '1')
        })
        
        return session
    
    def fetch_page(self, url, timeout=None):
        """Fetch a single page with error handling"""
        if timeout is None:
            timeout = self.config.get('network.timeout', 15)
            
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to fetch {url}: {e}")
            return None
    
    def close(self):
        """Close the session"""
        if hasattr(self, 'session'):
            self.session.close()
    
    def __del__(self):
        """Cleanup resources"""
        self.close() 
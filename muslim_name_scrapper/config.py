#!/usr/bin/env python3
"""
Configuration management module
Handles loading and accessing configuration from YAML file with fallbacks
"""

import os
import logging
from pathlib import Path
from typing import Any, Dict, Optional

# Try to import yaml for configuration loading
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class Config:
    """Configuration manager with YAML support and fallback defaults"""
    
    # Hardcoded fallback configuration (same structure as config.yml)
    DEFAULT_CONFIG = {
        'app': {
            'name': 'Muslim Names Scraper',
            'version': '2.0.0',
            'author': 'Md Takiuddin',
            'email': 'contact@takiuddin.me'
        },
        'scraper': {
            'base_url': 'https://muslimnames.com',
            'max_workers': 16,
            'max_retries': 3,
            'backoff_factor': 0.3,
            'default_output_dir': 'data',
            'urls': {
                'boy_names': '/boy-names',
                'girl_names': '/girl-names'
            }
        },
        'network': {
            'timeout': 15,
            'max_connections': 32,
            'max_size_multiplier': 2,
            'headers': {
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'accept_language': 'en-US,en;q=0.5',
                'accept_encoding': 'gzip, deflate',
                'connection': 'keep-alive',
                'upgrade_insecure_requests': '1'
            },
            'retry': {
                'total': 3,
                'backoff_factor': 0.3,
                'status_forcelist': [429, 500, 502, 503, 504],
                'allowed_methods': ['HEAD', 'GET', 'OPTIONS'],
                'method_whitelist': ['HEAD', 'GET', 'OPTIONS']
            }
        },
        'parser': {
            'name_row_class': 'name_row',
            'boy_names_class': 'name_boys',
            'girl_names_class': 'name_girls',
            'arabic_name_class': 'name_arabic',
            'pagination_style_contains': 'text-align:center'
        },
        'storage': {
            'csv': {
                'fieldnames': ['english_name', 'arabic_name', 'meaning', 'url', 'gender'],
                'encoding': 'utf-8'
            },
            'database': {
                'table_name': 'names',
                'schema': {
                    'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
                    'english_name': 'TEXT NOT NULL',
                    'arabic_name': 'TEXT',
                    'meaning': 'TEXT',
                    'url': 'TEXT',
                    'gender': 'TEXT NOT NULL',
                    'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
                },
                'indexes': [
                    {'name': 'idx_english_name', 'column': 'english_name'},
                    {'name': 'idx_gender', 'column': 'gender'},
                    {'name': 'idx_arabic_name', 'column': 'arabic_name'}
                ]
            },
            'file_patterns': {
                'csv': 'muslim_names.csv',
                'json': 'muslim_names.json',
                'sqlite': 'muslim_names.db',
                'progress': 'progress.json'
            }
        },
        'progress': {
            'save_interval': 10,
            'bar_format': '{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]',
            'unit': 'page'
        },
        'logging': {
            'level': 'INFO',
            'format': '%(asctime)s - %(levelname)s - %(message)s',
            'file': 'scraper.log',
            'console': True,
            'file_logging': True
        },
        'kaggle': {
            'default_license': 'CC0-1.0',
            'default_public': True,
            'keywords': ['religion', 'names', 'islam', 'muslim', 'dataset', 'culture', 'linguistics'],
            'description_template': """# Muslim Names Dataset

A comprehensive collection of Muslim names with meanings scraped from muslimnames.com.

## Dataset Contents

This dataset contains {name_count} Muslim names with the following information:
- English name
- Arabic name (in Arabic script)
- Meaning/definition
- Source URL
- Gender classification (male/female)

## Files Included

- **CSV**: Spreadsheet-compatible format for easy analysis
- **JSON**: Machine-readable format for developers
- **SQLite**: Database format for SQL queries

## Data Source

Data scraped from [muslimnames.com](https://muslimnames.com) using an automated scraper with respectful rate limiting.

## Usage

Perfect for:
- Cultural and linguistic research
- Name analysis and statistics
- Baby naming applications
- Islamic studies
- Data science projects

## License

This dataset is made available under the Creative Commons CC0 1.0 Universal license.

    **Scraper Version:** {version}"""
        },
        'cli': {
            'default_workers': 16,
            'test_mode_pages': 2,
            'description': 'Scrape Muslim names from muslimnames.com',
            'examples': """Examples:
  python -m muslim_name_scrapper                        # Scrape all names
  python -m muslim_name_scrapper --test                 # Test mode (2 pages per gender)
  python -m muslim_name_scrapper --max-pages 5          # Limit to 5 pages per gender
  python -m muslim_name_scrapper --workers 8            # Use 8 workers
  python -m muslim_name_scrapper --output-dir data      # Custom output directory
  python -m muslim_name_scrapper --upload-kaggle        # Upload to Kaggle after scraping
  python -m muslim_name_scrapper --kaggle-title "My Dataset" --upload-kaggle  # Custom Kaggle title"""
        },
        'performance': {
            'batch_size': 100,
            'max_memory_mb': 1024,
            'min_workers': 1,
            'max_workers': 64,
            'delay_between_requests': 0.1,
            'retry_delay': 2.0
        }
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager
        
        Args:
            config_file: Path to YAML config file. If None, looks for config.yml in project root
        """
        self.logger = logging.getLogger(__name__)
        self._config = self.DEFAULT_CONFIG.copy()
        self._config_file = config_file
        
        # Try to load configuration from YAML file
        self._load_config()
    
    def _find_config_file(self) -> Optional[Path]:
        """Find the configuration file in various locations"""
        if self._config_file:
            config_path = Path(self._config_file)
            if config_path.exists():
                return config_path
        
        # Look for config.yml in common locations
        search_paths = [
            Path.cwd() / "config.yml",  # Current directory
            Path(__file__).parent.parent / "config.yml",  # Project root
            Path.home() / ".muslim_name_scrapper" / "config.yml",  # User home
        ]
        
        for path in search_paths:
            if path.exists():
                return path
        
        return None
    
    def _load_config(self):
        """Load configuration from YAML file"""
        if not HAS_YAML:
            self.logger.warning("PyYAML not installed. Using default configuration.")
            self.logger.info("Install with: pip install PyYAML")
            return
        
        config_path = self._find_config_file()
        if not config_path:
            self.logger.info("No config.yml found. Using default configuration.")
            return
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                yaml_config = yaml.safe_load(f)
            
            if yaml_config:
                self._merge_config(yaml_config)
                self.logger.info(f"Configuration loaded from: {config_path}")
            else:
                self.logger.warning(f"Empty configuration file: {config_path}")
                
        except Exception as e:
            self.logger.error(f"Failed to load configuration from {config_path}: {e}")
            self.logger.info("Using default configuration.")
    
    def _merge_config(self, yaml_config: Dict[str, Any]):
        """Merge YAML configuration with defaults"""
        def merge_dict(default: Dict, override: Dict) -> Dict:
            """Recursively merge dictionaries"""
            result = default.copy()
            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = merge_dict(result[key], value)
                else:
                    result[key] = value
            return result
        
        self._config = merge_dict(self._config, yaml_config)
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        
        Args:
            key_path: Dot-separated path to config value (e.g., 'scraper.max_workers')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self._config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any):
        """
        Set configuration value using dot notation
        
        Args:
            key_path: Dot-separated path to config value
            value: Value to set
        """
        keys = key_path.split('.')
        config = self._config
        
        # Navigate to the parent dictionary
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # Set the final value
        config[keys[-1]] = value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section
        
        Args:
            section: Section name (e.g., 'scraper', 'network')
            
        Returns:
            Configuration section as dictionary
        """
        return self._config.get(section, {})
    
    def save_config(self, file_path: Optional[str] = None):
        """
        Save current configuration to YAML file
        
        Args:
            file_path: Path to save config file. If None, saves to config.yml in current directory
        """
        if not HAS_YAML:
            self.logger.error("PyYAML not installed. Cannot save configuration.")
            return False
        
        save_path = Path(file_path) if file_path else Path.cwd() / "config.yml"
        
        try:
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._config, f, default_flow_style=False, sort_keys=False, indent=2)
            
            self.logger.info(f"Configuration saved to: {save_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            return False
    
    def __repr__(self):
        """String representation of configuration"""
        return f"Config(sections={list(self._config.keys())})"


# Global configuration instance
_config_instance = None


def get_config(config_file: Optional[str] = None) -> Config:
    """
    Get global configuration instance (singleton pattern)
    
    Args:
        config_file: Path to config file (only used on first call)
        
    Returns:
        Configuration instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_file)
    return _config_instance


def reload_config(config_file: Optional[str] = None):
    """
    Reload configuration (creates new instance)
    
    Args:
        config_file: Path to config file
    """
    global _config_instance
    _config_instance = Config(config_file) 
#!/usr/bin/env python3
"""
Parser module for HTML content processing
"""

import logging
from bs4 import BeautifulSoup
from .config import get_config


class HTMLParser:
    """Handles HTML parsing operations"""
    
    def __init__(self, base_url=None):
        # Load configuration
        self.config = get_config()
        
        # Use config value as default, allow override via parameter
        self.base_url = base_url or self.config.get('scraper.base_url', 'https://muslimnames.com')
        self.logger = logging.getLogger(__name__)
    
    def parse_names_from_page(self, html_content, gender, page_num=None):
        """Parse names from a single page HTML content"""
        if not html_content:
            return []
            
        soup = BeautifulSoup(html_content, 'html.parser')
        names = []
        
        # Get CSS class names from configuration
        name_row_class = self.config.get('parser.name_row_class', 'name_row')
        boy_names_class = self.config.get('parser.boy_names_class', 'name_boys')
        girl_names_class = self.config.get('parser.girl_names_class', 'name_girls')
        arabic_name_class = self.config.get('parser.arabic_name_class', 'name_arabic')
        
        # Find all name entries
        name_rows = soup.find_all('div', class_=name_row_class)
        
        for row in name_rows:
            try:
                # Extract English name using config class names
                class_name = boy_names_class if gender == 'male' else girl_names_class
                english_name_element = row.find('a', class_=class_name)
                if not english_name_element:
                    continue
                    
                english_name = english_name_element.get_text().strip()
                
                # Extract Arabic name using config class name
                arabic_name_element = row.find('b', class_=arabic_name_class)
                arabic_name = arabic_name_element.get_text().strip() if arabic_name_element else ""
                
                # Extract meaning
                full_text = row.get_text()
                lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                meaning = lines[-1] if len(lines) > 1 else ""
                
                # Extract URL
                url = english_name_element.get('href', '') if english_name_element else ""
                if url and not url.startswith('http'):
                    url = f"{self.base_url}{url}"
                
                name_data = {
                    'english_name': english_name,
                    'arabic_name': arabic_name,
                    'meaning': meaning,
                    'url': url,
                    'gender': gender
                }
                
                names.append(name_data)
                
            except Exception as e:
                self.logger.error(f"Error parsing name row on page {page_num}: {e}")
                continue
        
        return names
    
    def get_page_count(self, html_content):
        """Extract total number of pages from HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Get pagination style pattern from config
        pagination_style_contains = self.config.get('parser.pagination_style_contains', 'text-align:center')
        
        try:
            page_info = soup.find('div', style=lambda value: value and pagination_style_contains in value)
            if page_info:
                text = page_info.get_text()
                if 'of' in text:
                    parts = text.split('of')
                    if len(parts) > 1:
                        return int(parts[1].strip().split()[0])
        except Exception as e:
            self.logger.error(f"Error extracting page count: {e}")
        return None 
#!/usr/bin/env python3
"""
Progress tracking module for monitoring scraping progress
"""

import json
import logging
from datetime import datetime

# Try to import tqdm for progress bars
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False


class ProgressTracker:
    """Handles progress tracking and monitoring"""
    
    def __init__(self, progress_file=None):
        self.progress_file = progress_file
        self.logger = logging.getLogger(__name__)
        self.progress_bars = {}
    
    def save_progress(self, completed_pages_male, completed_pages_female, total_names):
        """Save current progress to file"""
        if not self.progress_file:
            return
            
        progress_data = {
            'completed_pages_male': completed_pages_male,
            'completed_pages_female': completed_pages_female,
            'total_names_scraped': total_names,
            'last_updated': datetime.now().isoformat()
        }
        
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(progress_data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving progress: {e}")
    
    def create_progress_bar(self, name, total, desc=None):
        """Create a new progress bar"""
        if HAS_TQDM:
            self.progress_bars[name] = tqdm(total=total, desc=desc or name, unit="page")
            return self.progress_bars[name]
        return None
    
    def update_progress_bar(self, name, **kwargs):
        """Update progress bar"""
        if HAS_TQDM and name in self.progress_bars:
            pbar = self.progress_bars[name]
            if 'postfix' in kwargs:
                pbar.set_postfix(kwargs['postfix'])
            if 'increment' in kwargs:
                pbar.update(kwargs['increment'])
    
    def close_progress_bar(self, name):
        """Close a progress bar"""
        if HAS_TQDM and name in self.progress_bars:
            self.progress_bars[name].close()
            del self.progress_bars[name]
    
    def close_all_progress_bars(self):
        """Close all progress bars"""
        for name in list(self.progress_bars.keys()):
            self.close_progress_bar(name)
    
    def load_progress(self):
        """Load progress from file"""
        if not self.progress_file:
            return None
            
        try:
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None
    
    def __del__(self):
        """Cleanup resources"""
        self.close_all_progress_bars() 
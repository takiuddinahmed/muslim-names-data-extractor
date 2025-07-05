#!/usr/bin/env python3
"""
Kaggle uploader module for uploading datasets to Kaggle
"""

import os
import json
import logging
import tempfile
import shutil
from pathlib import Path


class KaggleUploader:
    """Handles uploading datasets to Kaggle"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.kaggle_api = None
        self._check_kaggle_setup()
    
    def _check_kaggle_setup(self):
        """Check if Kaggle API is properly configured"""
        try:
            import kaggle
            self.kaggle_api = kaggle.api
            self.kaggle_api.authenticate()
            self.logger.info("Kaggle API authenticated successfully")
        except ImportError:
            self.logger.error("Kaggle package not installed. Install with: pip install kaggle")
            raise ImportError("Kaggle package required. Install with: pip install kaggle")
        except Exception as e:
            self.logger.error(f"Kaggle authentication failed: {e}")
            self.logger.info("Make sure you have ~/.kaggle/kaggle.json with your API credentials")
            raise
    
    def create_dataset_metadata(self, title, description, files, license_name="CC0-1.0"):
        """Create dataset metadata for Kaggle"""
        # Get file information
        dataset_files = []
        for file_path in files:
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                dataset_files.append({
                    "path": os.path.basename(file_path),
                    "description": f"Muslim names data in {os.path.splitext(file_path)[1][1:].upper()} format"
                })
        
        metadata = {
            "title": title,
            "id": f"{self.kaggle_api.get_config_value('username')}/{title.lower().replace(' ', '-').replace('_', '-')}",
            "licenses": [{"name": license_name}],
            "description": description,
            "files": dataset_files,
            "keywords": ["religion", "names", "islam", "muslim", "dataset", "culture", "linguistics"]
        }
        
        return metadata
    
    def upload_dataset(self, files, title=None, description=None, public=True, update_existing=False):
        """Upload dataset to Kaggle"""
        if not files:
            raise ValueError("No files provided for upload")
        
        # Validate files exist
        valid_files = []
        for file_path in files:
            if os.path.exists(file_path):
                valid_files.append(file_path)
            else:
                self.logger.warning(f"File not found: {file_path}")
        
        if not valid_files:
            raise ValueError("No valid files found for upload")
        
        # Generate default title and description if not provided
        timestamp = Path(valid_files[0]).stem.split('_')[-1] if '_' in Path(valid_files[0]).stem else "latest"
        
        if not title:
            title = f"Muslim Names Dataset {timestamp}"
        
        if not description:
            description = f"""
# Muslim Names Dataset

A comprehensive collection of Muslim names with meanings scraped from muslimnames.com.

## Dataset Contents

This dataset contains {self._estimate_name_count(valid_files)} Muslim names with the following information:
- English name
- Arabic name (in Arabic script)
- Meaning/definition
- Source URL
- Gender classification (male/female)

## Files Included

- **CSV**: Spreadsheet-compatible format for easy analysis
- **JSON**: Machine-readable format for developers
- **SQLite**: Database format for SQL queries
- **Progress**: Metadata about scraping progress

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

**Generated on:** {timestamp}
**Scraper Version:** 2.0.0
            """.strip()
        
        try:
            # Create temporary directory for dataset
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Copy files to temp directory
                for file_path in valid_files:
                    dest_path = temp_path / Path(file_path).name
                    shutil.copy2(file_path, dest_path)
                    self.logger.info(f"Copied {file_path} to temporary directory")
                
                # Create dataset metadata
                metadata = self.create_dataset_metadata(
                    title=title,
                    description=description,
                    files=valid_files
                )
                
                # Write metadata to temp directory
                metadata_path = temp_path / "dataset-metadata.json"
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2)
                
                self.logger.info(f"Created dataset metadata: {metadata_path}")
                
                # Upload or update dataset
                dataset_slug = metadata["id"].split('/')[-1]
                
                if update_existing:
                    try:
                        # Try to update existing dataset
                        self.kaggle_api.dataset_create_version(
                            folder=str(temp_path),
                            version_notes=f"Updated dataset with latest scraped data - {timestamp}",
                            quiet=False
                        )
                        self.logger.info(f"Successfully updated existing dataset: {metadata['id']}")
                        return {
                            'success': True,
                            'dataset_url': f"https://www.kaggle.com/datasets/{metadata['id']}",
                            'action': 'updated',
                            'dataset_id': metadata['id']
                        }
                    except Exception as e:
                        self.logger.warning(f"Failed to update existing dataset: {e}")
                        self.logger.info("Attempting to create new dataset instead...")
                
                # Create new dataset
                self.kaggle_api.dataset_create_new(
                    folder=str(temp_path),
                    public=public,
                    quiet=False
                )
                
                self.logger.info(f"Successfully created new dataset: {metadata['id']}")
                
                return {
                    'success': True,
                    'dataset_url': f"https://www.kaggle.com/datasets/{metadata['id']}",
                    'action': 'created',
                    'dataset_id': metadata['id']
                }
                
        except Exception as e:
            self.logger.error(f"Failed to upload dataset to Kaggle: {e}")
            return {
                'success': False,
                'error': str(e),
                'action': 'failed'
            }
    
    def _estimate_name_count(self, files):
        """Estimate number of names from files"""
        for file_path in files:
            if file_path.endswith('.csv'):
                try:
                    # Count lines in CSV (excluding header)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        line_count = sum(1 for line in f) - 1  # Exclude header
                    return f"~{line_count:,}"
                except Exception:
                    pass
        return "thousands of"
    
    def list_user_datasets(self):
        """List user's existing datasets"""
        try:
            username = self.kaggle_api.get_config_value('username')
            datasets = self.kaggle_api.dataset_list(user=username)
            return [dataset.ref for dataset in datasets]
        except Exception as e:
            self.logger.error(f"Failed to list user datasets: {e}")
            return []
    
    def check_dataset_exists(self, dataset_title):
        """Check if a dataset with similar title already exists"""
        user_datasets = self.list_user_datasets()
        dataset_slug = dataset_title.lower().replace(' ', '-').replace('_', '-')
        
        for dataset_ref in user_datasets:
            if dataset_slug in dataset_ref.lower():
                return dataset_ref
        return None 
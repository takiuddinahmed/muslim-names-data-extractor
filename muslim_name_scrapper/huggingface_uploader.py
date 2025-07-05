#!/usr/bin/env python3
"""
Hugging Face uploader module for uploading datasets to Hugging Face Hub
"""

import os
import json
import logging
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Optional


class HuggingFaceUploader:
    """Handles uploading datasets to Hugging Face Hub"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.hf_api = None
        self._check_huggingface_setup()
    
    def _check_huggingface_setup(self):
        """Check if Hugging Face Hub is properly configured"""
        try:
            from huggingface_hub import HfApi, login
            from huggingface_hub.utils import HfFolder
            
            # Check if token exists
            token = HfFolder.get_token()
            if not token:
                self.logger.error("No Hugging Face token found. Please login with: huggingface-cli login")
                raise ValueError("Hugging Face authentication required")
            
            self.hf_api = HfApi()
            # Test authentication
            user_info = self.hf_api.whoami()
            self.logger.info(f"Hugging Face API authenticated successfully as: {user_info['name']}")
            
        except ImportError:
            self.logger.error("huggingface_hub package not installed. Install with: pip install huggingface_hub")
            raise ImportError("huggingface_hub package required. Install with: pip install huggingface_hub")
        except Exception as e:
            self.logger.error(f"Hugging Face authentication failed: {e}")
            self.logger.info("Make sure you're logged in with: huggingface-cli login")
            raise
    
    def create_dataset_card(self, title: str, description: str, files: List[str], tags: List[str] = None) -> str:
        """Create a dataset card (README.md) for Hugging Face"""
        if tags is None:
            tags = ["religion", "names", "islam", "muslim", "dataset", "culture", "linguistics"]
        
        # Estimate dataset size
        name_count = self._estimate_name_count(files)
        file_info = self._get_file_info(files)
        
        card_content = f"""---
license: cc0-1.0
language:
- en
- ar
tags:
{chr(10).join(f'- {tag}' for tag in tags)}
size_categories:
- 10K<n<100K
task_categories:
- text-classification
- text-generation
pretty_name: {title}
dataset_info:
  features:
  - name: english_name
    dtype: string
  - name: arabic_name
    dtype: string
  - name: meaning
    dtype: string
  - name: gender
    dtype: string
  splits:
  - name: train
    num_bytes: {file_info['total_size']}
    num_examples: {file_info['estimated_rows']}
  download_size: {file_info['total_size']}
  dataset_size: {file_info['total_size']}
configs:
- config_name: default
  data_files:
  - split: train
    path: "*.csv"
---

# {title}

{description}

## Dataset Contents

This dataset contains **{name_count}** Muslim names with the following information:
- **English name**: Name in English/Latin script
- **Arabic name**: Name in Arabic script
- **Meaning**: Definition and meaning of the name
- **Gender**: Classification as male or female

## Files Included

{chr(10).join(f'- **{Path(f).name}**: {self._get_file_description(f)}' for f in files)}

## Data Source

Data scraped from [muslimnames.com](https://muslimnames.com) using an automated scraper with respectful rate limiting.

## Usage

### Loading the Dataset

```python
from datasets import load_dataset

dataset = load_dataset("USERNAME/DATASET_NAME")
# Replace USERNAME/DATASET_NAME with the actual dataset path
```

### Example Usage

```python
import pandas as pd

# Load CSV directly
df = pd.read_csv("muslim_names.csv")

# Filter by gender
male_names = df[df['gender'] == 'male']
female_names = df[df['gender'] == 'female']

# Search for names with specific meanings
spiritual_names = df[df['meaning'].str.contains('Allah|God|prayer', case=False, na=False)]
```

## Applications

Perfect for:
- Cultural and linguistic research
- Name analysis and statistics
- Baby naming applications
- Islamic studies and research
- Data science projects
- Natural language processing
- Cultural AI applications

## Data Quality

- **Completeness**: All names include English transliteration and meaning
- **Accuracy**: Data sourced from established Islamic names database
- **Consistency**: Standardized format across all entries
- **Encoding**: Proper UTF-8 encoding for Arabic text

## License

This dataset is made available under the **Creative Commons CC0 1.0 Universal** license, placing it in the public domain.

## Citation

If you use this dataset in your research, please cite:

```
@dataset{{muslim_names_dataset,
  title={{Muslim Names Dataset}},
  author={{Takiuddin Ahmed}},
  year={{2025}},
  url={{https://huggingface.co/datasets/USERNAME/DATASET_NAME}},
  note={{Comprehensive collection of Muslim names with meanings}}
}}
```

## Acknowledgments

- Data source: [muslimnames.com](https://muslimnames.com)
- Scraper: [Muslim Names Data Extractor](https://github.com/takiuddinahmed/muslim-names-data-extractor)
"""
        
        return card_content
    
    def upload_dataset(self, files: List[str], title: str = None, description: str = None, 
                      private: bool = False, update_existing: bool = False, 
                      dataset_id: str = None) -> Dict:
        """Upload dataset to Hugging Face Hub"""
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
        if not title:
            title = "Muslim Names Dataset"
        
        if not description:
            description = f"""A comprehensive collection of Muslim names with meanings scraped from muslimnames.com.

This dataset contains {self._estimate_name_count(valid_files)} Muslim names with English names, Arabic names, meanings, and gender classifications.

Data was collected using an automated scraper with respectful rate limiting from muslimnames.com."""
        
        # Generate dataset ID if not provided
        if not dataset_id:
            username = self.hf_api.whoami()['name']
            dataset_slug = title.lower().replace(' ', '-').replace('_', '-')
            dataset_id = f"{username}/{dataset_slug}"
        
        try:
            # Create dataset repository
            if not update_existing:
                try:
                    self.hf_api.create_repo(
                        repo_id=dataset_id,
                        repo_type="dataset",
                        private=private,
                        exist_ok=update_existing
                    )
                    self.logger.info(f"Created dataset repository: {dataset_id}")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        self.logger.info(f"Dataset repository already exists: {dataset_id}")
                    else:
                        raise
            
            # Create dataset card
            card_content = self.create_dataset_card(title, description, valid_files)
            
            # Upload files
            uploaded_files = []
            for file_path in valid_files:
                filename = Path(file_path).name
                
                # Upload file
                self.hf_api.upload_file(
                    path_or_fileobj=file_path,
                    path_in_repo=filename,
                    repo_id=dataset_id,
                    repo_type="dataset",
                    commit_message=f"Upload {filename}"
                )
                
                uploaded_files.append(filename)
                self.logger.info(f"Uploaded {filename} to {dataset_id}")
            
            # Upload dataset card (README.md)
            self.hf_api.upload_file(
                path_or_fileobj=card_content.encode('utf-8'),
                path_in_repo="README.md",
                repo_id=dataset_id,
                repo_type="dataset",
                commit_message="Add dataset card"
            )
            
            self.logger.info(f"Uploaded dataset card to {dataset_id}")
            
            # Return success info
            return {
                'success': True,
                'dataset_url': f"https://huggingface.co/datasets/{dataset_id}",
                'action': 'updated' if update_existing else 'created',
                'dataset_id': dataset_id,
                'uploaded_files': uploaded_files
            }
            
        except Exception as e:
            self.logger.error(f"Failed to upload dataset to Hugging Face: {e}")
            return {
                'success': False,
                'error': str(e),
                'action': 'failed'
            }
    
    def _estimate_name_count(self, files: List[str]) -> str:
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
    
    def _get_file_info(self, files: List[str]) -> Dict:
        """Get file information for dataset card"""
        total_size = 0
        estimated_rows = 0
        
        for file_path in files:
            if os.path.exists(file_path):
                total_size += os.path.getsize(file_path)
                
                # Estimate rows from CSV
                if file_path.endswith('.csv'):
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            estimated_rows = sum(1 for line in f) - 1  # Exclude header
                    except Exception:
                        pass
        
        return {
            'total_size': total_size,
            'estimated_rows': estimated_rows or 1000  # Default estimate
        }
    
    def _get_file_description(self, file_path: str) -> str:
        """Get description for file type"""
        ext = Path(file_path).suffix.lower()
        descriptions = {
            '.csv': 'Comma-separated values format for spreadsheet analysis',
            '.json': 'JSON format for programmatic access',
            '.db': 'SQLite database format for SQL queries',
            '.txt': 'Plain text format'
        }
        return descriptions.get(ext, 'Data file')
    
    def list_user_datasets(self) -> List[str]:
        """List user's existing datasets"""
        try:
            username = self.hf_api.whoami()['name']
            datasets = self.hf_api.list_datasets(author=username)
            return [dataset.id for dataset in datasets]
        except Exception as e:
            self.logger.error(f"Failed to list user datasets: {e}")
            return []
    
    def check_dataset_exists(self, dataset_title: str) -> Optional[str]:
        """Check if a dataset with similar title already exists"""
        user_datasets = self.list_user_datasets()
        dataset_slug = dataset_title.lower().replace(' ', '-').replace('_', '-')
        
        for dataset_id in user_datasets:
            if dataset_slug in dataset_id.lower():
                return dataset_id
        return None 
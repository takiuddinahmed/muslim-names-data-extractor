#!/usr/bin/env python3
"""
Main scraper module that orchestrates all components
"""

import time
import logging
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from .network import NetworkManager
from .parser import HTMLParser
from .storage import DataStorage
from .progress import ProgressTracker
from .config import get_config

# Configure logging based on config
config = get_config()
logging.basicConfig(
    level=getattr(logging, config.get('logging.level', 'INFO')),
    format=config.get('logging.format', '%(asctime)s - %(levelname)s - %(message)s'),
    handlers=[
        logging.FileHandler(config.get('logging.file', 'scraper.log')),
        logging.StreamHandler()
    ] if config.get('logging.console', True) and config.get('logging.file_logging', True) else [
        logging.StreamHandler()
    ] if config.get('logging.console', True) else [
        logging.FileHandler(config.get('logging.file', 'scraper.log'))
    ]
)


class MuslimNamesScraper:
    """Main scraper class that orchestrates all components"""
    
    def __init__(self, max_workers=None, max_retries=None, backoff_factor=None):
        # Load configuration
        self.config = get_config()
        
        # Use config values as defaults, allow override via parameters
        self.base_url = self.config.get('scraper.base_url')
        self.max_workers = max_workers or self.config.get('scraper.max_workers')
        self.max_retries = max_retries or self.config.get('scraper.max_retries')
        self.backoff_factor = backoff_factor or self.config.get('scraper.backoff_factor')
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize components with config
        self.network_manager = NetworkManager(self.max_workers, self.max_retries, self.backoff_factor)
        self.html_parser = HTMLParser(self.base_url)
        self.data_storage = None
        self.progress_tracker = None
        
        # Thread-safe lock
        self.lock = threading.Lock()
    
    def scrape_page(self, args):
        """Scrape a single page and save data immediately"""
        page_num, gender, base_url = args
        
        page_url = base_url if page_num == 1 else f"{base_url}?page={page_num}"
        
        # Fetch page content
        html_content = self.network_manager.fetch_page(page_url)
        if html_content:
            # Parse names from HTML
            names = self.html_parser.parse_names_from_page(html_content, gender, page_num)
            
            # Save data immediately
            if names:
                self.data_storage.save_names_batch(names, page_num, gender)
            
            return {'page': page_num, 'count': len(names), 'success': True}
        else:
            return {'page': page_num, 'count': 0, 'success': False}
    
    def scrape_gender_names(self, gender, max_pages=None):
        """Scrape all names for a given gender with parallel processing"""
        # Use config URLs
        url_key = 'boy_names' if gender == 'male' else 'girl_names'
        gender_url = self.config.get(f'scraper.urls.{url_key}')
        base_url = f"{self.base_url}{gender_url}"
        
        self.logger.info(f"Starting scrape of {gender} names from {base_url}")
        
        # Get total pages from first page
        first_page_html = self.network_manager.fetch_page(base_url)
        if not first_page_html:
            self.logger.error(f"Failed to fetch first page for {gender} names")
            return []
        
        total_pages = self.html_parser.get_page_count(first_page_html)
        if total_pages is None:
            self.logger.warning(f"Could not determine total pages for {gender} names, defaulting to 10")
            total_pages = 10
        
        if max_pages:
            total_pages = min(total_pages, max_pages)
        
        self.logger.info(f"Scraping {total_pages} pages for {gender} names using {self.max_workers} workers")
        
        # Prepare page arguments
        page_args = [(page, gender, base_url) for page in range(1, total_pages + 1)]
        
        completed_pages = []
        failed_pages = []
        
        # Create progress bar
        pbar = self.progress_tracker.create_progress_bar(
            f"{gender}_progress", 
            total_pages, 
            f"Scraping {gender} names"
        )
        
        # Execute parallel scraping
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_page = {executor.submit(self.scrape_page, args): args[0] for args in page_args}
            
            for future in as_completed(future_to_page):
                page_num = future_to_page[future]
                try:
                    result = future.result()
                    if result['success']:
                        completed_pages.append(page_num)
                        self.progress_tracker.update_progress_bar(
                            f"{gender}_progress",
                            postfix={'Names': self.data_storage.get_total_count(), 'Page': page_num},
                            increment=1
                        )
                    else:
                        failed_pages.append(page_num)
                        self.logger.warning(f"Failed to scrape page {page_num}")
                except Exception as e:
                    failed_pages.append(page_num)
                    self.logger.error(f"Error processing page {page_num}: {e}")
        
        # Close progress bar
        self.progress_tracker.close_progress_bar(f"{gender}_progress")
        
        # Retry failed pages
        if failed_pages:
            self.logger.info(f"Retrying {len(failed_pages)} failed pages for {gender} names")
            self._retry_failed_pages(failed_pages, gender, base_url, completed_pages)
        
        self.logger.info(f"Total {gender} pages completed: {len(completed_pages)}")
        return completed_pages
    
    def _retry_failed_pages(self, failed_pages, gender, base_url, completed_pages):
        """Retry failed pages with backoff delay"""
        retry_delay = self.config.get('performance.retry_delay', 2.0)
        
        for page_num in failed_pages:
            try:
                time.sleep(retry_delay)  # Wait before retry
                result = self.scrape_page((page_num, gender, base_url))
                if result['success']:
                    completed_pages.append(page_num)
                    self.logger.info(f"Successfully retried page {page_num} for {gender}")
                else:
                    self.logger.error(f"Failed to retry page {page_num} for {gender}")
            except Exception as e:
                self.logger.error(f"Error retrying page {page_num}: {e}")
    
    def scrape_gender_worker(self, gender, max_pages, results_dict):
        """Worker function for parallel gender scraping"""
        try:
            completed_pages = self.scrape_gender_names(gender, max_pages)
            with self.lock:
                results_dict[gender] = completed_pages
        except Exception as e:
            self.logger.error(f"Error scraping {gender} names: {e}")
            with self.lock:
                results_dict[gender] = []
    
    def upload_to_kaggle(self, file_paths, title=None, description=None, public=None, update_existing=False):
        """Upload scraped data to Kaggle"""
        try:
            from .kaggle_uploader import KaggleUploader
            
            # Prepare files for upload (exclude progress file)
            upload_files = [
                file_paths['csv'],
                file_paths['json'],
                file_paths['sqlite']
            ]
            
            # Use config defaults if not specified
            if public is None:
                public = self.config.get('kaggle.default_public', True)
            
            kaggle_uploader = KaggleUploader()
            
            self.logger.info("Starting Kaggle dataset upload...")
            result = kaggle_uploader.upload_dataset(
                files=upload_files,
                title=title,
                description=description,
                public=public,
                update_existing=update_existing
            )
            
            if result['success']:
                self.logger.info(f"Successfully {result['action']} Kaggle dataset!")
                self.logger.info(f"Dataset URL: {result['dataset_url']}")
            else:
                self.logger.error(f"Failed to upload to Kaggle: {result['error']}")
            
            return result
            
        except ImportError:
            self.logger.error("Kaggle package not installed. Install with: pip install kaggle")
            return {'success': False, 'error': 'Kaggle package not installed', 'action': 'failed'}
        except Exception as e:
            self.logger.error(f"Error uploading to Kaggle: {e}")
            return {'success': False, 'error': str(e), 'action': 'failed'}
    
    def upload_to_huggingface(self, file_paths, title=None, description=None, private=None, update_existing=False, dataset_id=None):
        """Upload scraped data to Hugging Face Hub"""
        try:
            from .huggingface_uploader import HuggingFaceUploader
            
            # Prepare files for upload (exclude progress file)
            upload_files = [
                file_paths['csv'],
                file_paths['json'],
                file_paths['sqlite']
            ]
            
            # Use config defaults if not specified
            if private is None:
                private = self.config.get('huggingface.default_private', False)
            
            hf_uploader = HuggingFaceUploader()
            
            self.logger.info("Starting Hugging Face dataset upload...")
            result = hf_uploader.upload_dataset(
                files=upload_files,
                title=title,
                description=description,
                private=private,
                update_existing=update_existing,
                dataset_id=dataset_id
            )
            
            if result['success']:
                self.logger.info(f"Successfully {result['action']} Hugging Face dataset!")
                self.logger.info(f"Dataset URL: {result['dataset_url']}")
            else:
                self.logger.error(f"Failed to upload to Hugging Face: {result['error']}")
            
            return result
            
        except ImportError:
            self.logger.error("huggingface_hub package not installed. Install with: pip install huggingface_hub")
            return {'success': False, 'error': 'huggingface_hub package not installed', 'action': 'failed'}
        except Exception as e:
            self.logger.error(f"Error uploading to Hugging Face: {e}")
            return {'success': False, 'error': str(e), 'action': 'failed'}
    
    def scrape_all(self, output_dir=None, max_pages=None, upload_kaggle=False, kaggle_title=None, kaggle_public=None, kaggle_update=False, upload_huggingface=False, hf_title=None, hf_private=None, hf_update=False, hf_dataset_id=None):
        """Main method to scrape all names with immediate saving and optional uploads"""
        start_time = time.time()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Use config default for output_dir if not specified
        if output_dir is None:
            output_dir = self.config.get('scraper.default_output_dir', 'data')
        
        self.logger.info("Starting Muslim Names Scraper with Immediate Saves")
        self.logger.info("=" * 60)
        
        try:
            # Initialize components with config
            self.data_storage = DataStorage(output_dir)
            file_paths = self.data_storage.initialize_files(timestamp)
            
            self.progress_tracker = ProgressTracker(file_paths['progress'])
            
            # Results dictionary for parallel execution
            results = {}
            
            # Create threads for parallel gender scraping
            threads = []
            for gender in ['male', 'female']:
                thread = threading.Thread(
                    target=self.scrape_gender_worker,
                    args=(gender, max_pages, results)
                )
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            # Get completed pages
            completed_male_pages = results.get('male', [])
            completed_female_pages = results.get('female', [])
            
            # Save final progress
            self.progress_tracker.save_progress(
                completed_male_pages, 
                completed_female_pages, 
                self.data_storage.get_total_count()
            )
            
            # Finalize JSON output
            self.data_storage.save_json_final(file_paths['json'])
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            self.logger.info(f"Scraping completed in {execution_time:.2f} seconds")
            self.logger.info(f"Total names scraped: {self.data_storage.get_total_count()}")
            self.logger.info(f"Male pages completed: {len(completed_male_pages)}")
            self.logger.info(f"Female pages completed: {len(completed_female_pages)}")
            self.logger.info("All data saved with immediate writes!")
            
            # Calculate statistics
            scraped_names = self.data_storage.get_scraped_names()
            boy_names = len([n for n in scraped_names if n['gender'] == 'male'])
            girl_names = len([n for n in scraped_names if n['gender'] == 'female'])
            
            result = {
                'total_names': self.data_storage.get_total_count(),
                'boy_names': boy_names,
                'girl_names': girl_names,
                'execution_time': execution_time,
                'completed_pages': {
                    'male': len(completed_male_pages),
                    'female': len(completed_female_pages)
                },
                'files': file_paths
            }
            
            # Upload to Kaggle if requested
            if upload_kaggle:
                kaggle_result = self.upload_to_kaggle(
                    file_paths=file_paths,
                    title=kaggle_title,
                    public=kaggle_public,
                    update_existing=kaggle_update
                )
                result['kaggle'] = kaggle_result
            
            # Upload to Hugging Face if requested
            if upload_huggingface:
                hf_result = self.upload_to_huggingface(
                    file_paths=file_paths,
                    title=hf_title,
                    private=hf_private,
                    update_existing=hf_update,
                    dataset_id=hf_dataset_id
                )
                result['huggingface'] = hf_result
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error during scraping: {e}")
            raise
        finally:
            # Cleanup resources
            self._cleanup()
    
    def _cleanup(self):
        """Cleanup all resources"""
        if self.data_storage:
            self.data_storage.close_files()
        if self.progress_tracker:
            self.progress_tracker.close_all_progress_bars()
        if self.network_manager:
            self.network_manager.close()
    
    def __del__(self):
        """Cleanup resources"""
        self._cleanup() 
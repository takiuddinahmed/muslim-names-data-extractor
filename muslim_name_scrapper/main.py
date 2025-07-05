#!/usr/bin/env python3
"""
Main script for Muslim Names Scraper
Run this script to scrape all Muslim names from muslimnames.com
"""

import argparse
import sys
from .scraper import MuslimNamesScraper
from .config import get_config


def main():
    """Main function to run the scraper with command line arguments"""
    # Load configuration
    config = get_config()
    
    # Get CLI configuration
    cli_config = config.get_section('cli')
    
    parser = argparse.ArgumentParser(
        description=cli_config.get('description', 'Scrape Muslim names from muslimnames.com'),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=cli_config.get('examples', 'See documentation for usage examples')
    )
    
    parser.add_argument(
        '--max-pages', type=int, default=None,
        help='Maximum number of pages to scrape per gender (default: all pages)'
    )
    
    parser.add_argument(
        '--output-dir', type=str, 
        default=config.get('scraper.default_output_dir', 'data'),
        help=f'Directory to save output files (default: {config.get("scraper.default_output_dir", "data")})'
    )
    
    parser.add_argument(
        '--test', action='store_true',
        help=f'Run in test mode (scrape only {cli_config.get("test_mode_pages", 2)} pages per gender)'
    )
    
    parser.add_argument(
        '--workers', type=int, 
        default=cli_config.get('default_workers', 16),
        help=f'Number of parallel workers (default: {cli_config.get("default_workers", 16)})'
    )
    
    parser.add_argument(
        '--no-progress', action='store_true',
        help='Disable progress bars'
    )
    
    # Kaggle upload options
    parser.add_argument(
        '--upload-kaggle', action='store_true',
        help='Upload dataset to Kaggle after scraping'
    )
    
    parser.add_argument(
        '--kaggle-title', type=str, default=None,
        help='Custom title for Kaggle dataset (default: auto-generated)'
    )
    
    parser.add_argument(
        '--kaggle-private', action='store_true',
        help=f'Make Kaggle dataset private (default: {"private" if not config.get("kaggle.default_public", True) else "public"})'
    )
    
    parser.add_argument(
        '--kaggle-update', action='store_true',
        help='Update existing Kaggle dataset instead of creating new one'
    )
    
    # Configuration options
    parser.add_argument(
        '--config', type=str, default=None,
        help='Path to custom configuration file (YAML format)'
    )
    
    args = parser.parse_args()
    
    # Reload configuration with custom config file if provided
    if args.config:
        from .config import reload_config
        reload_config(args.config)
        config = get_config()
    
    # Set max_pages based on test mode
    if args.test:
        max_pages = cli_config.get('test_mode_pages', 2)
        print(f"Running in test mode - scraping {max_pages} pages per gender")
    else:
        max_pages = args.max_pages
    
    # Disable progress bars if requested
    if args.no_progress:
        import muslim_name_scrapper.progress as progress_module
        progress_module.HAS_TQDM = False
    
    try:
        # Initialize and run scraper with config-aware defaults
        scraper = MuslimNamesScraper(max_workers=args.workers)
        result = scraper.scrape_all(
            output_dir=args.output_dir, 
            max_pages=max_pages,
            upload_kaggle=args.upload_kaggle,
            kaggle_title=args.kaggle_title,
            kaggle_public=not args.kaggle_private,
            kaggle_update=args.kaggle_update
        )
        
        # Display results
        print("\n" + "="*60)
        print("SCRAPING SUMMARY")
        print("="*60)
        print(f"Total names scraped: {result['total_names']}")
        print(f"Boy names: {result['boy_names']}")
        print(f"Girl names: {result['girl_names']}")
        print(f"Execution time: {result['execution_time']:.2f} seconds")
        print(f"Average speed: {result['total_names']/result['execution_time']:.2f} names/second")
        print(f"Workers used: {args.workers}")
        
        print(f"\nPages completed:")
        print(f"  👦 Male pages: {result['completed_pages']['male']}")
        print(f"  👧 Female pages: {result['completed_pages']['female']}")
        
        print(f"\nOutput files:")
        print(f"  📄 JSON: {result['files']['json']}")
        print(f"  📊 CSV: {result['files']['csv']}")
        print(f"  🗃️  SQLite: {result['files']['sqlite']}")
        print(f"  📝 Progress: {result['files']['progress']}")
        
        # Display Kaggle upload results
        if args.upload_kaggle and 'kaggle' in result:
            kaggle_result = result['kaggle']
            print(f"\nKaggle Upload:")
            if kaggle_result['success']:
                print(f"  ✅ Successfully {kaggle_result['action']} dataset")
                print(f"  🔗 URL: {kaggle_result['dataset_url']}")
                print(f"  🆔 Dataset ID: {kaggle_result['dataset_id']}")
            else:
                print(f"  ❌ Upload failed: {kaggle_result['error']}")
        
        # Display configuration info
        print(f"\nConfiguration:")
        print(f"  📁 Config loaded: {'Yes' if config._find_config_file() else 'No (using defaults)'}")
        if args.config:
            print(f"  📄 Custom config: {args.config}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
        return 1
    except Exception as e:
        print(f"Error occurred: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 
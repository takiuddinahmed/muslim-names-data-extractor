#!/usr/bin/env python3
"""
Simple script to run the Muslim Names Scraper
"""

from muslim_name_scrapper.scraper import MuslimNamesScraper


def main():
    """Run the scraper with default settings and optional Kaggle upload"""
    print("🚀 Starting Muslim Names Scraper...")
    print("=" * 50)
    
    # Ask user for preferences
    print("Configuration options:")
    test_mode = input("Run in test mode? (y/N): ").lower().strip() in ['y', 'yes']
    
    kaggle_upload = False
    kaggle_title = None
    try:
        # Check if kaggle is available
        from muslim_name_scrapper.kaggle_uploader import KaggleUploader
        kaggle_choice = input("Upload to Kaggle after scraping? (y/N): ").lower().strip()
        if kaggle_choice in ['y', 'yes']:
            kaggle_upload = True
            custom_title = input("Custom dataset title (press Enter for auto-generated): ").strip()
            if custom_title:
                kaggle_title = custom_title
    except ImportError:
        print("📝 Note: Kaggle package not installed - skipping Kaggle upload option")
    
    print("\n🔧 Initializing scraper...")
    
    # Initialize scraper with optimized settings
    scraper = MuslimNamesScraper(max_workers=16)
    
    # Run scraper
    try:
        results = scraper.scrape_all(
            max_pages=2 if test_mode else None,
            upload_kaggle=kaggle_upload,
            kaggle_title=kaggle_title
        )
        
        # Display results
        print("\n📊 Scraping Results:")
        print(f"   Total Names: {results['total_names']}")
        print(f"   Boy Names: {results['boy_names']}")
        print(f"   Girl Names: {results['girl_names']}")
        print(f"   Execution Time: {results['execution_time']:.2f} seconds")
        print(f"   Average Speed: {results['total_names']/results['execution_time']:.2f} names/second")
        
        print(f"\n📑 Pages Completed:")
        print(f"   Male Pages: {results['completed_pages']['male']}")
        print(f"   Female Pages: {results['completed_pages']['female']}")
        
        print(f"\n📁 Files Created:")
        for file_type, path in results['files'].items():
            print(f"   {file_type.upper()}: {path}")
        
        # Display Kaggle results if applicable
        if kaggle_upload and 'kaggle' in results:
            kaggle_result = results['kaggle']
            print(f"\n🔗 Kaggle Upload:")
            if kaggle_result['success']:
                print(f"   ✅ Successfully {kaggle_result['action']} dataset")
                print(f"   📊 Dataset URL: {kaggle_result['dataset_url']}")
                print(f"   🆔 Dataset ID: {kaggle_result['dataset_id']}")
            else:
                print(f"   ❌ Upload failed: {kaggle_result['error']}")
        
    except KeyboardInterrupt:
        print("\n❌ Scraping interrupted by user")
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")


if __name__ == "__main__":
    main() 
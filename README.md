# Muslim Names Scraper

A robust Python scraper for extracting Muslim names with meanings from [muslimnames.com](https://muslimnames.com). Features parallel processing, immediate data saving, and multiple output formats.

## Features

- **Parallel Processing**: Optimized for speed with configurable workers
- **Immediate Data Saving**: Data is saved as pages are scraped (no memory bloat)
- **Multiple Output Formats**: JSON, CSV, and SQLite
- **Progress Tracking**: Real-time progress bars and checkpoint saving
- **Error Handling**: Automatic retry logic and graceful failure handling
- **Resume Capability**: Track completed pages for recovery
- **Kaggle Integration**: Automatic dataset upload to Kaggle
- **Configuration-Driven**: YAML-based configuration for easy customization

## Installation

1. Clone the repository:
```bash
git clone https://github.com/takiuddinahmed/muslim-names-data-extractor.git
cd muslim-names-data-extractor
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. (Optional) Setup Kaggle for dataset uploads:
```bash
# Install Kaggle API
pip install kaggle

# Setup Kaggle credentials
# 1. Go to https://www.kaggle.com/settings/account
# 2. Create new API token (downloads kaggle.json)
# 3. Place kaggle.json in ~/.kaggle/ directory
# 4. Set permissions: chmod 600 ~/.kaggle/kaggle.json
```

## Usage

### Simple Usage
```bash
python run_scraper.py
```

### Command Line Interface
```bash
# Scrape all names
python -m muslim_name_scrapper

# Test mode (2 pages per gender)
python -m muslim_name_scrapper --test

# Limit pages and workers
python -m muslim_name_scrapper --max-pages 5 --workers 8

# Custom output directory
python -m muslim_name_scrapper --output-dir my_data

# Upload to Kaggle after scraping
python -m muslim_name_scrapper --upload-kaggle

# Custom Kaggle dataset with private visibility
python -m muslim_name_scrapper --upload-kaggle --kaggle-title "My Muslim Names Dataset" --kaggle-private
```

### Python API

#### Complete Scraper
```python
from muslim_name_scrapper import MuslimNamesScraper

# Initialize scraper
scraper = MuslimNamesScraper(max_workers=16)

# Run scraper
results = scraper.scrape_all(output_dir="data", max_pages=None)

print(f"Total names scraped: {results['total_names']}")
```

#### Individual Components
```python
from muslim_name_scrapper import NetworkManager, HTMLParser, DataStorage

# Use individual components
network = NetworkManager(max_workers=8)
parser = HTMLParser("https://muslimnames.com")
storage = DataStorage("output")

# Fetch and parse a page
html = network.fetch_page("https://muslimnames.com/boy-names")
names = parser.parse_names_from_page(html, "male", 1)

# Save data
file_paths = storage.initialize_files("20240101_120000")
storage.save_names_batch(names, 1, "male")
```

#### Kaggle Upload
```python
from muslim_name_scrapper import MuslimNamesScraper

# Scrape and upload to Kaggle in one step
scraper = MuslimNamesScraper()
results = scraper.scrape_all(
    upload_kaggle=True,
    kaggle_title="Muslim Names Dataset 2024",
    kaggle_public=True
)

# Or upload existing files separately
from muslim_name_scrapper import KaggleUploader

uploader = KaggleUploader()
result = uploader.upload_dataset(
    files=["data/names.csv", "data/names.json", "data/names.db"],
    title="Muslim Names Dataset",
    description="Comprehensive collection of Muslim names",
    public=True
)
```

## Configuration

The scraper uses a YAML configuration file (`config.yml`) for easy customization:

### Default Settings
- **Workers**: 16 parallel workers
- **Output Directory**: `data/`
- **Retry Attempts**: 3 attempts per failed page
- **Output Formats**: JSON, CSV, SQLite

### Performance Optimization
The scraper is optimized for your system:
- **Recommended Workers**: 16 (balanced performance)
- **Conservative**: 8 workers
- **Aggressive**: 32 workers

## Output Files

Each scraping session creates timestamped files:
- `muslim_names_YYYYMMDD_HHMMSS.json` - JSON format
- `muslim_names_YYYYMMDD_HHMMSS.csv` - CSV format
- `muslim_names_YYYYMMDD_HHMMSS.db` - SQLite database
- `progress_YYYYMMDD_HHMMSS.json` - Progress tracking

## Data Structure

Each name entry contains:
```json
{
  "english_name": "Ahmad",
  "arabic_name": "أحمد",
  "meaning": "Most commendable, most praiseworthy",
  "gender": "male"
}
```

## Performance

- **Estimated Dataset**: ~14,585 names total
- **Execution Time**: 40-50 seconds for full dataset
- **Speed**: 300+ names/second
- **Memory Usage**: Constant (data saved immediately)

## Project Structure

```
muslim-name-scrapper/
├── muslim_name_scrapper/          # Main package (modular architecture)
│   ├── __init__.py               # Package initialization
│   ├── main.py                   # CLI interface
│   ├── scraper.py                # Main orchestrator
│   ├── network.py                # HTTP operations
│   ├── parser.py                 # HTML parsing
│   ├── storage.py                # Data persistence
│   ├── progress.py               # Progress tracking
│   ├── kaggle_uploader.py        # Kaggle dataset uploads
│   ├── config.py                 # Configuration management
│   └── __main__.py               # Entry point
├── config.yml                     # YAML configuration file
├── run_scraper.py                # Simple run script
├── requirements.txt              # Dependencies
└── README.md                     # This file
```

## Architecture

The scraper follows a modular architecture with clear separation of concerns:

- **`scraper.py`**: Main orchestrator that coordinates all components
- **`network.py`**: Handles HTTP requests, session management, and connection pooling
- **`parser.py`**: Processes HTML content and extracts name data
- **`storage.py`**: Manages data persistence (CSV, SQLite, JSON)
- **`progress.py`**: Tracks and displays scraping progress
- **`kaggle_uploader.py`**: Handles dataset uploads to Kaggle platform
- **`config.py`**: Configuration management with YAML support

## Requirements

- Python 3.7+
- requests
- beautifulsoup4
- tqdm (optional, for progress bars)
- PyYAML (optional, for YAML configuration)

## Error Handling

The scraper includes robust error handling:
- Automatic retry for failed pages
- Graceful handling of network issues
- Safe file operations with proper cleanup
- Progress tracking for resumption

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is for educational and research purposes. Please respect the terms of service of the source website.

## Support

For issues or questions, please open an issue on the GitHub repository. 
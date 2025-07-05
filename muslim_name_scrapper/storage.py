#!/usr/bin/env python3
"""
Storage module for data persistence operations
"""

import csv
import json
import sqlite3
import os
import logging
from threading import Lock
from .config import get_config


class DataStorage:
    """Handles data storage operations for CSV, SQLite, and JSON formats"""
    
    def __init__(self, output_dir=None, timestamp=None):
        # Load configuration
        self.config = get_config()
        
        # Use config default if not specified
        self.output_dir = output_dir or self.config.get('scraper.default_output_dir', 'data')
        self.timestamp = timestamp
        self.logger = logging.getLogger(__name__)
        self.lock = Lock()
        
        # File handles
        self.csv_file = None
        self.csv_writer = None
        self.db_connection = None
        
        # Data collection
        self.scraped_names = []
    
    def initialize_files(self, timestamp):
        """Initialize output files for immediate writing"""
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Get file patterns from config
        file_patterns = self.config.get_section('storage.file_patterns')
        csv_pattern = file_patterns.get('csv', 'muslim_names_{timestamp}.csv')
        sqlite_pattern = file_patterns.get('sqlite', 'muslim_names_{timestamp}.db')
        json_pattern = file_patterns.get('json', 'muslim_names_{timestamp}.json')
        progress_pattern = file_patterns.get('progress', 'progress_{timestamp}.json')
        
        # Initialize CSV file with config settings
        csv_path = os.path.join(self.output_dir, csv_pattern.format(timestamp=timestamp))
        csv_config = self.config.get_section('storage.csv')
        encoding = csv_config.get('encoding', 'utf-8')
        fieldnames = csv_config.get('fieldnames', ['english_name', 'arabic_name', 'meaning', 'url', 'gender'])
        
        self.csv_file = open(csv_path, 'w', newline='', encoding=encoding)
        self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=fieldnames)
        self.csv_writer.writeheader()
        
        # Initialize SQLite database with config schema
        db_path = os.path.join(self.output_dir, sqlite_pattern.format(timestamp=timestamp))
        self.db_connection = sqlite3.connect(db_path, check_same_thread=False)
        cursor = self.db_connection.cursor()
        
        # Get database configuration
        db_config = self.config.get_section('storage.database')
        table_name = db_config.get('table_name', 'names')
        schema = db_config.get('schema', {})
        
        # Build CREATE TABLE statement from config schema with proper error handling
        if schema:
            try:
                schema_parts = []
                for column, definition in schema.items():
                    # Ensure definition is a string and clean it
                    if isinstance(definition, str):
                        clean_definition = definition.strip()
                        if clean_definition:
                            schema_parts.append(f"{column} {clean_definition}")
                
                if schema_parts:
                    create_table_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(schema_parts)})"
                    self.logger.debug(f"Creating table with SQL: {create_table_sql}")
                    cursor.execute(create_table_sql)
                else:
                    raise ValueError("No valid schema parts found")
            except Exception as e:
                self.logger.warning(f"Error creating table from config schema: {e}")
                self.logger.info("Using default schema instead")
                self._create_default_table(cursor, table_name)
        else:
            self._create_default_table(cursor, table_name)
        
        # Create indexes from config
        try:
            indexes = db_config.get('indexes', [])
            for index_config in indexes:
                if isinstance(index_config, dict):
                    index_name = index_config.get('name')
                    column = index_config.get('column')
                    if index_name and column:
                        index_sql = f'CREATE INDEX IF NOT EXISTS {index_name} ON {table_name}({column})'
                        self.logger.debug(f"Creating index with SQL: {index_sql}")
                        cursor.execute(index_sql)
        except Exception as e:
            self.logger.warning(f"Error creating indexes: {e}")
        
        self.db_connection.commit()
        
        return {
            'csv': csv_path,
            'sqlite': db_path,
            'json': os.path.join(self.output_dir, json_pattern.format(timestamp=timestamp)),
            'progress': os.path.join(self.output_dir, progress_pattern.format(timestamp=timestamp))
        }
    
    def _create_default_table(self, cursor, table_name):
        """Create table with default schema as fallback"""
        default_sql = f'''
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                english_name TEXT NOT NULL,
                arabic_name TEXT,
                meaning TEXT,
                url TEXT,
                gender TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        '''
        cursor.execute(default_sql)
        
        # Create default indexes
        default_indexes = [
            f'CREATE INDEX IF NOT EXISTS idx_english_name ON {table_name}(english_name)',
            f'CREATE INDEX IF NOT EXISTS idx_gender ON {table_name}(gender)',
            f'CREATE INDEX IF NOT EXISTS idx_arabic_name ON {table_name}(arabic_name)'
        ]
        
        for index_sql in default_indexes:
            cursor.execute(index_sql)
    
    def save_names_batch(self, names, page_num, gender):
        """Save a batch of names from a single page immediately"""
        if not names:
            return
            
        with self.lock:
            try:
                # Add to in-memory collection
                self.scraped_names.extend(names)
                
                # Write to CSV immediately
                for name in names:
                    self.csv_writer.writerow(name)
                self.csv_file.flush()
                
                # Write to SQLite immediately using config table name
                table_name = self.config.get('storage.database.table_name', 'names')
                cursor = self.db_connection.cursor()
                
                insert_sql = f'''
                    INSERT INTO {table_name} (english_name, arabic_name, meaning, url, gender)
                    VALUES (?, ?, ?, ?, ?)
                '''
                cursor.executemany(insert_sql, [
                    (name['english_name'], name['arabic_name'], name['meaning'], 
                     name['url'], name['gender']) for name in names
                ])
                self.db_connection.commit()
                
                self.logger.info(f"Saved {len(names)} names from {gender} page {page_num} (Total: {len(self.scraped_names)})")
                
            except Exception as e:
                self.logger.error(f"Error saving page data: {e}")
    
    def save_json_final(self, json_path):
        """Save final JSON file from scraped data"""
        try:
            encoding = self.config.get('storage.csv.encoding', 'utf-8')
            with open(json_path, 'w', encoding=encoding) as f:
                json.dump(self.scraped_names, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Saved {len(self.scraped_names)} names to {json_path}")
        except Exception as e:
            self.logger.error(f"Error saving JSON to {json_path}: {e}")
    
    def get_scraped_names(self):
        """Get all scraped names"""
        return self.scraped_names
    
    def get_total_count(self):
        """Get total number of scraped names"""
        return len(self.scraped_names)
    
    def close_files(self):
        """Close all open file handles"""
        try:
            if self.csv_file:
                self.csv_file.close()
                self.csv_file = None
            if self.db_connection:
                self.db_connection.close()
                self.db_connection = None
        except Exception as e:
            self.logger.error(f"Error closing files: {e}")
    
    def __del__(self):
        """Cleanup resources"""
        self.close_files() 
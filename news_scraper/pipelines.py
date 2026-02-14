import json
import os
from datetime import datetime
from pathlib import Path


class NewsScraperPipeline:
    """Pipeline to process and save news items"""
    
    def open_spider(self, spider):
        """Executed when the spider is opened"""
        # Create data directory if it doesn't exist
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        
        # Create output file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"news_{spider.name}_{timestamp}.json"
        self.file_path = self.data_dir / filename
        
        self.file = open(self.file_path, 'w', encoding='utf-8')
        self.items = []
        
    def close_spider(self, spider):
        """Executed when the spider is closed"""
        # Save all items in JSON format
        json.dump(self.items, self.file, ensure_ascii=False, indent=2)
        self.file.close()
        
        spider.logger.info(f"Data saved to: {self.file_path}")
        spider.logger.info(f"Total news scraped: {len(self.items)}")
        
    def process_item(self, item, spider):
        """Processes each scraped item"""
        # Add scraping timestamp
        item['scraped_at'] = datetime.now().isoformat()
        
        # Clean empty fields
        cleaned_item = {k: v for k, v in dict(item).items() if v}
        
        self.items.append(cleaned_item)
        return item

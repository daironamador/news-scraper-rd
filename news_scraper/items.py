import scrapy


class NewsItem(scrapy.Item):
    """Item to store news data"""
    
    title = scrapy.Field()
    url = scrapy.Field()
    author = scrapy.Field()
    published_date = scrapy.Field()
    content = scrapy.Field()
    summary = scrapy.Field()
    category = scrapy.Field()
    tags = scrapy.Field()
    image_url = scrapy.Field()
    source = scrapy.Field()
    scraped_at = scrapy.Field()

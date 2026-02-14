from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class NewsArticle(BaseModel):
    """Model for a news article"""
    title: str
    url: str
    author: Optional[str] = None
    published_date: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = []
    image_url: Optional[str] = None
    source: Optional[str] = None
    scraped_at: Optional[str] = None


class ScrapeRequest(BaseModel):
    """Model for scrape request"""
    spider_name: str = Field(
        default="diariolibre",
        description="Name of the spider to execute"
    )
    urls: Optional[List[str]] = Field(
        default=None,
        description="Specific URLs to scrape (optional)"
    )
    max_pages: Optional[int] = Field(
        default=10,
        description="Maximum number of pages to scrape"
    )


class ScrapeResponse(BaseModel):
    """Model for scrape response"""
    status: str
    message: str
    job_id: Optional[str] = None
    total_items: Optional[int] = None
    file_path: Optional[str] = None


class CategoryCount(BaseModel):
    """Count of articles by category"""
    category: str
    count: int


class SourceCount(BaseModel):
    """Count of articles by source"""
    source: str
    count: int

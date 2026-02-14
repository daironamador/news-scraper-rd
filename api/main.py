from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import subprocess
import json
import os
from pathlib import Path
from datetime import datetime
from typing import List
import uuid

from api.models import NewsArticle, ScrapeRequest, ScrapeResponse, CategoryCount, SourceCount

app = FastAPI(
    title="ScrapeNews API",
    description="API para escrapear noticias de sitios web usando Scrapy",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data directory
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# In-memory job storage (use Redis or DB in production)
jobs = {}


def run_scrapy_spider(spider_name: str, job_id: str, urls: List[str] = None):
    """Executes a Scrapy spider in the background"""
    try:
        output_file = DATA_DIR / f"news_{job_id}.json"
        
        cmd = [
            "scrapy", "crawl", spider_name,
            "-o", str(output_file),
            "-s", f"JOBDIR=crawls/{job_id}"
        ]
        
        # Add custom URLs if provided
        if urls:
            cmd.extend(["-a", f"start_urls={','.join(urls)}"])
        
        # Execute spider
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path.cwd()
        )
        
        # Update job status
        if result.returncode == 0:
            # Count scraped items
            if output_file.exists():
                with open(output_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    total_items = len(data) if isinstance(data, list) else 1
            else:
                total_items = 0
            
            jobs[job_id] = {
                "status": "completed",
                "total_items": total_items,
                "file_path": str(output_file),
                "completed_at": datetime.now().isoformat()
            }
        else:
            jobs[job_id] = {
                "status": "failed",
                "error": result.stderr,
                "completed_at": datetime.now().isoformat()
            }
    
    except Exception as e:
        jobs[job_id] = {
            "status": "failed",
            "error": str(e),
            "completed_at": datetime.now().isoformat()
        }


def _load_all_news() -> list:
    """Loads all news from JSON files"""
    all_news = []
    for json_file in DATA_DIR.glob("news_*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    all_news.extend(data)
                else:
                    all_news.append(data)
        except Exception as e:
            print(f"Error reading {json_file}: {e}")
    return all_news


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "ScrapeNews API",
        "version": "1.0.0",
        "description": "API to scrape news from websites using Scrapy",
        "endpoints": {
            "POST /scrape": "Start news scraping",
            "GET /jobs/{job_id}": "Get job status",
            "GET /news": "List all scraped news",
            "GET /news/{job_id}": "Get news from a specific job",
            "GET /news/filter": "Filter news by category, source and/or date",
            "GET /news/categories": "List categories with count",
            "GET /news/sources": "List sources with count",
            "GET /spiders": "List available spiders",
            "GET /docs": "Interactive documentation (Swagger UI)"
        }
    }


@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_news(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks
):
    """
    Starts news scraping in the background.
    
    - **spider_name**: Name of the spider to execute (default: news_spider)
    - **urls**: List of URLs to scrape (optional)
    - **max_pages**: Maximum number of pages (optional)
    """
    try:
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        
        # Register job
        jobs[job_id] = {
            "status": "running",
            "spider": request.spider_name,
            "started_at": datetime.now().isoformat()
        }
        
        # Execute spider in background
        background_tasks.add_task(
            run_scrapy_spider,
            request.spider_name,
            job_id,
            request.urls
        )
        
        return ScrapeResponse(
            status="started",
            message=f"Scraping started with spider '{request.spider_name}'",
            job_id=job_id
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Gets the status of a scraping job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return jobs[job_id]


@app.get("/news", response_model=List[NewsArticle])
async def get_all_news(limit: int = 100):
    """
    Gets all scraped news.

    - **limit**: Maximum number of news to return
    """
    all_news = _load_all_news()
    all_news.sort(key=lambda x: x.get('scraped_at', ''), reverse=True)
    return all_news[:limit]


@app.get("/news/filter", response_model=List[NewsArticle])
async def filter_news(
    category: str = None,
    source: str = None,
    date_from: str = None,
    date_to: str = None,
    limit: int = 100
):
    """
    Filters news by category, source, and/or date range.

    - **category**: Filter by category (partial search, case-insensitive)
    - **source**: Filter by source (e.g., "Diario Libre", "Listin Diario")
    - **date_from**: Start date YYYY-MM-DD
    - **date_to**: End date YYYY-MM-DD
    - **limit**: Maximum results (default 100)
    """
    all_news = _load_all_news()
    filtered = all_news

    if category:
        cat_lower = category.lower()
        filtered = [
            n for n in filtered
            if n.get('category') and cat_lower in n['category'].lower()
        ]

    if source:
        src_lower = source.lower()
        filtered = [
            n for n in filtered
            if n.get('source') and src_lower in n['source'].lower()
        ]

    if date_from:
        filtered = [
            n for n in filtered
            if n.get('published_date', '') >= date_from
        ]

    if date_to:
        date_to_end = date_to + "T23:59:59"
        filtered = [
            n for n in filtered
            if n.get('published_date', '') <= date_to_end
        ]

    filtered.sort(key=lambda x: x.get('published_date', ''), reverse=True)
    return filtered[:limit]


@app.get("/news/categories", response_model=List[CategoryCount])
async def get_categories():
    """Returns all categories with their article count"""
    all_news = _load_all_news()
    counts = {}
    for article in all_news:
        cat = article.get('category')
        if cat:
            counts[cat] = counts.get(cat, 0) + 1

    result = [CategoryCount(category=k, count=v) for k, v in counts.items()]
    result.sort(key=lambda x: x.count, reverse=True)
    return result


@app.get("/news/sources", response_model=List[SourceCount])
async def get_sources():
    """Returns all sources with their article count"""
    all_news = _load_all_news()
    counts = {}
    for article in all_news:
        src = article.get('source')
        if src:
            counts[src] = counts.get(src, 0) + 1

    result = [SourceCount(source=k, count=v) for k, v in counts.items()]
    result.sort(key=lambda x: x.count, reverse=True)
    return result


@app.get("/news/{job_id}", response_model=List[NewsArticle])
async def get_news_by_job(job_id: str):
    """Gets news from a specific job"""
    file_path = DATA_DIR / f"news_{job_id}.json"
    
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="No news found for this job"
        )
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, list) else [data]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/spiders")
async def list_spiders():
    """Lists available spiders"""
    try:
        result = subprocess.run(
            ["scrapy", "list"],
            capture_output=True,
            text=True,
            cwd=Path.cwd()
        )
        
        if result.returncode == 0:
            spiders = result.stdout.strip().split('\n')
            return {
                "spiders": spiders,
                "total": len(spiders)
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Error listing spiders"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/news/{job_id}")
async def delete_news(job_id: str):
    """Deletes news from a specific job"""
    file_path = DATA_DIR / f"news_{job_id}.json"
    
    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="No news found for this job"
        )
    
    try:
        file_path.unlink()
        if job_id in jobs:
            del jobs[job_id]
        
        return {"message": f"Noticias del trabajo {job_id} eliminadas"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

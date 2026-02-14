# 📰 News Scraper RD

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Scrapy](https://img.shields.io/badge/scrapy-2.12.0-green.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-teal.svg)

**News Scraper RD** is a robust news scraping system for the Dominican Republic with a REST API. It extracts articles from the main newspapers of the Dominican Republic using Scrapy and exposes the data through FastAPI.

It combines the power of **Scrapy** for efficient crawling with **FastAPI** to serve the data via a modern RESTful API.

## 🚀 Features

- **Multi-Source Scraping**: Supports multiple news outlets including _Diario Libre_, _Listín Diario_, _El Nuevo Diario_, and _El Nacional_.
- **RESTful API**: Exposes scraped data through a comprehensive API with filtering and search capabilities.
- **Background Jobs**: Trigger scraping jobs asynchronously via the API.
- **Data Export**: Automatically saves scraped data to JSON files (configurable for databases).
- **Respectful Crawling**: Implements delays and respects `robots.txt` to ensure ethical scraping.

## 📂 Project Structure

```
ScrapeNews/
├── api/
│   ├── main.py              # FastAPI application and endpoints
│   └── models.py            # Pydantic models for data validation
├── news_scraper/
│   ├── spiders/             # Scrapy spiders for each newspaper
│   ├── items.py             # Data models for scraped items
│   ├── pipelines.py         # Item processing pipelines
│   └── settings.py          # Scrapy configuration (User-Agents, Delays)
├── data/                    # Output directory for scraped JSON files
├── scrapy.cfg               # Scrapy project configuration
├── requirements.txt         # Project dependencies
└── run_spider.bat           # Helper script for running spiders
```

## 🛠️ Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/yourusername/ScrapeNews.git
    cd ScrapeNews
    ```

2.  **Create a virtual environment:**

    ```bash
    python -m venv venv

    # Windows
    venv\Scripts\activate

    # Linux/Mac
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## 📖 Usage

### Running Spiders Locally

You can run individual spiders directly using Scrapy:

```bash
# List available spiders
scrapy list

# Run a specific spider
scrapy crawl diariolibre
scrapy crawl listindiario
```

Or use the provided batch script (Windows):

```bat
run_spider.bat
```

### Running the API

Start the FastAPI server to interact with the data programmatically:

```bash
python -m uvicorn api.main:app --reload
```

The API will be available at `http://localhost:8000`.

### API Docs

Access the interactive API documentation (Swagger UI) at:
`http://localhost:8000/docs`

#### Key Endpoints:

- `POST /scrape`: Trigger a scraping job in the background.
- `GET /news`: Retrieve all scraped news (supports pagination).
- `GET /news/filter`: Filter news by category, source, date, etc.
- `GET /news/categories`: Get a list of available news categories.

## 📊 Data Format

Each scraped article contains the following fields:

```json
{
  "title": "Article Headline",
  "url": "https://example.com/article...",
  "author": "Journalist Name",
  "published_date": "2026-02-14",
  "content": "Full text of the article...",
  "summary": "Brief summary or lead paragraph",
  "category": "Politics",
  "tags": ["government", "policy"],
  "image_url": "https://example.com/image.jpg",
  "source": "Diario Libre",
  "scraped_at": "2026-02-14T10:00:00"
}
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1.  Fork the project
2.  Create your feature branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

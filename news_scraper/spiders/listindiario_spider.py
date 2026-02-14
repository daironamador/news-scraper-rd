import scrapy
import json
import re
from news_scraper.items import NewsItem


class ListinDiarioSpider(scrapy.Spider):
    """
    Spider configured for Listín Diario (listindiario.com)
    Dominican newspaper - crawls all sections of the site.
    """

    name = "listindiario"
    allowed_domains = ["listindiario.com"]

    sections = [
        "/",
        "/la-republica",
        "/economia",
        "/deportes",
        "/la-vida",
        "/entretenimiento",
        "/el-deporte",
        "/las-mundiales",
        "/puntos-de-vista",
    ]

    start_urls = [
        f"https://listindiario.com{section}" for section in sections
    ]

    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'ROBOTSTXT_OBEY': True,
    }

    # Article URLs: /section/YYYYMMDD/slug_ID.html
    article_url_pattern = re.compile(r'/\d{8}/.*\.html$')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.seen_urls = set()

    def parse(self, response):
        """Extracts article links from each section"""

        links = response.css('a::attr(href)').getall()

        for link in links:
            if not link:
                continue

            full_url = response.urljoin(link)

            if 'listindiario.com' not in full_url:
                continue
            if not self.article_url_pattern.search(full_url):
                continue
            if full_url in self.seen_urls:
                continue

            self.seen_urls.add(full_url)
            yield scrapy.Request(full_url, callback=self.parse_article)

    def parse_article(self, response):
        """Extracts data from an individual article"""

        item = NewsItem()

        # Extract JSON-LD (main source for Listín Diario)
        article_data = self._extract_jsonld(response)

        # Title
        item['title'] = (
            article_data.get('headline')
            or response.css('h1::text').get('').strip()
        )

        item['url'] = response.url

        # Author
        author = article_data.get('author')
        if isinstance(author, dict):
            author = author.get('name')
        elif isinstance(author, list) and author:
            author = author[0].get('name') if isinstance(author[0], dict) else str(author[0])
        item['author'] = author or response.css('a[href*="/autor/"]::text').get()

        # Date
        item['published_date'] = (
            article_data.get('datePublished')
            or response.css('time::attr(datetime)').get()
        )

        # Content
        paragraphs = response.css('.c-article__closed p::text, .c-article__closed p *::text').getall()
        if not paragraphs:
            paragraphs = response.css('.c-article__subs p::text, .c-article__subs p *::text').getall()
        if not paragraphs:
            paragraphs = response.css('article p::text, article p *::text').getall()
        item['content'] = ' '.join(p.strip() for p in paragraphs if p.strip())

        # Summary
        item['summary'] = (
            article_data.get('description')
            or response.css('meta[property="og:description"]::attr(content)').get()
            or response.css('meta[name="description"]::attr(content)').get()
        )

        # Category
        item['category'] = (
            article_data.get('articleSection')
            or response.css('meta[name="category"]::attr(content)').get()
        )
        if not item.get('category'):
            parts = response.url.replace('https://listindiario.com/', '').split('/')
            if parts:
                item['category'] = parts[0].replace('-', ' ').title()

        # Tags
        keywords = article_data.get('keywords', '')
        if isinstance(keywords, str) and keywords:
            item['tags'] = [k.strip() for k in keywords.split(',') if k.strip()]
        else:
            item['tags'] = response.css('a[href*="/tag/"]::text').getall()

        # Image
        ld_image = article_data.get('image')
        if isinstance(ld_image, dict):
            ld_image = ld_image.get('url')
        elif isinstance(ld_image, list) and ld_image:
            ld_image = ld_image[0] if isinstance(ld_image[0], str) else ld_image[0].get('url', '')
        item['image_url'] = (
            response.css('meta[property="og:image"]::attr(content)').get()
            or ld_image
        )

        item['source'] = 'Listín Diario'

        if item.get('title') and item.get('content'):
            yield item

    def _extract_jsonld(self, response):
        """Extracts JSON-LD data of NewsArticle type"""
        for block in response.css('script[type="application/ld+json"]::text').getall():
            try:
                data = json.loads(block)
                if isinstance(data, dict) and data.get('@type') in ('NewsArticle', 'Article'):
                    return data
                if isinstance(data, list):
                    for d in data:
                        if isinstance(d, dict) and d.get('@type') in ('NewsArticle', 'Article'):
                            return d
            except (json.JSONDecodeError, TypeError):
                continue
        return {}

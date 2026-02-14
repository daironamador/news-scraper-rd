import scrapy
import json
import re
from news_scraper.items import NewsItem


class ElNacionalSpider(scrapy.Spider):
    """
    Spider configured for El Nacional (elnacional.com.do)
    Dominican newspaper - WordPress, crawls all sections.
    """

    name = "elnacional"
    allowed_domains = ["elnacional.com.do"]

    sections = [
        "/",
        "/secciones/actualidad/",
        "/secciones/deportes/",
        "/secciones/opinion/",
        "/secciones/economia/",
        "/secciones/mundo/",
        "/secciones/que-pasa/",
        "/secciones/reportajes/",
        "/secciones/semana/",
        "/secciones/pagina-dos/",
    ]

    start_urls = [
        f"https://elnacional.com.do{section}" for section in sections
    ]

    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'ROBOTSTXT_OBEY': True,
    }

    # Paths that are sections, not articles
    skip_patterns = {
        'secciones/', 'author/', 'tag/', 'page/', 'wp-',
        'wp-content/', 'wp-admin/', 'feed/', '#',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.seen_urls = set()

    def parse(self, response):
        """Extracts article links from each section"""

        links = response.css(
            'article a::attr(href), '
            '.entry-title a::attr(href), '
            'h2 a::attr(href), h3 a::attr(href), '
            '.wp-block-post-template a::attr(href)'
        ).getall()

        for link in links:
            if not link:
                continue

            full_url = response.urljoin(link)

            if 'elnacional.com.do' not in full_url:
                continue

            path = full_url.replace('https://elnacional.com.do/', '').strip('/')

            # Filter non-articles
            if not path:
                continue
            if any(skip in path for skip in self.skip_patterns):
                continue

            if full_url in self.seen_urls:
                continue

            self.seen_urls.add(full_url)
            yield scrapy.Request(full_url, callback=self.parse_article)

        # Pagination
        next_pages = response.css('a.next::attr(href), a[rel="next"]::attr(href)').getall()
        for page_link in next_pages:
            page_url = response.urljoin(page_link)
            if page_url not in self.seen_urls:
                self.seen_urls.add(page_url)
                yield scrapy.Request(page_url, callback=self.parse)

    def parse_article(self, response):
        """Extracts data from an individual article"""

        item = NewsItem()

        # Extract JSON-LD
        article_data = self._extract_jsonld(response)

        # Title
        item['title'] = (
            response.css('h1::text').get('').strip()
            or article_data.get('headline')
            or response.css('meta[property="og:title"]::attr(content)').get()
        )

        item['url'] = response.url

        # Author - in El Nacional JSON-LD uses @id for author, not name directly
        author = article_data.get('author')
        if isinstance(author, dict):
            author = author.get('name') or author.get('@id', '').split('/')[-2] if '/' in author.get('@id', '') else None
        elif isinstance(author, list) and author:
            a = author[0]
            author = a.get('name') if isinstance(a, dict) else str(a)
        item['author'] = (
            author
            or response.css('meta[name="author"]::attr(content)').get()
            or response.css('a[href*="/author/"]::text').get()
        )

        # Date
        item['published_date'] = (
            article_data.get('datePublished')
            or response.css('meta[property="article:published_time"]::attr(content)').get()
            or response.css('time::attr(datetime)').get()
        )

        # Content
        paragraphs = response.css('.entry-content p::text, .entry-content p *::text').getall()
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
            response.css('meta[property="article:section"]::attr(content)').get()
            or article_data.get('articleSection')
        )
        if not item.get('category'):
            # Extract from URL: /secciones/actualidad/ -> Actualidad
            match = re.search(r'/secciones/([^/]+)/', response.url)
            if match:
                item['category'] = match.group(1).replace('-', ' ').title()

        # Tags
        tags = response.css('meta[property="article:tag"]::attr(content)').getall()
        if not tags:
            keywords = article_data.get('keywords', '')
            if isinstance(keywords, str) and keywords:
                tags = [k.strip() for k in keywords.split(',') if k.strip()]
            else:
                tags = response.css('a[rel="tag"]::text').getall()
        item['tags'] = tags

        # Image
        item['image_url'] = (
            response.css('meta[property="og:image"]::attr(content)').get()
            or response.css('.entry-content img::attr(src)').get()
        )

        item['source'] = 'El Nacional'

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
                # WordPress @graph
                if isinstance(data, dict) and '@graph' in data:
                    for d in data['@graph']:
                        if isinstance(d, dict) and d.get('@type') in ('NewsArticle', 'Article'):
                            return d
            except (json.JSONDecodeError, TypeError):
                continue
        return {}

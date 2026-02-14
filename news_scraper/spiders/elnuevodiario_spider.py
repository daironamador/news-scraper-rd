import scrapy
import json
import re
from news_scraper.items import NewsItem


class ElNuevoDiarioSpider(scrapy.Spider):
    """
    Spider configured for El Nuevo Diario (elnuevodiario.com.do)
    Dominican newspaper - WordPress, crawls all sections.
    """

    name = "elnuevodiario"
    allowed_domains = ["elnuevodiario.com.do"]

    sections = [
        "/",
        "/nacionales/",
        "/politica/",
        "/economia/",
        "/deportes/",
        "/internacionales/",
        "/opinion/",
        "/editorial/",
        "/salud/",
        "/denuncias/",
        "/toga/",
        "/buenas-noticias/",
        "/sociales/",
        "/medio-ambiente/",
        "/sostenibilidad/",
        "/novedades/",
        "/viral/",
        "/new-york/",
        "/sabores/",
        "/mundo-otaku/",
    ]

    start_urls = [
        f"https://elnuevodiario.com.do{section}" for section in sections
    ]

    custom_settings = {
        'DOWNLOAD_DELAY': 3,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'ROBOTSTXT_OBEY': True,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 0.5,
        'RETRY_HTTP_CODES': [429, 500, 502, 503, 504],
        'RETRY_TIMES': 5,
        'HTTPCACHE_ENABLED': False,
    }

    # Exclude URLs that are sections/categories (not articles)
    section_paths = {s.strip('/') for s in sections if s != '/'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.seen_urls = set()

    def parse(self, response):
        """Extracts article links from each section"""

        # Specific selectors for El Nuevo Diario + generics
        links = response.css(
            '.noticia-principal a.title::attr(href), '
            '.noticia-regular a.title::attr(href), '
            '.noticia-opinion a.title::attr(href), '
            'article a::attr(href), '
            '.entry-title a::attr(href), '
            'h2 a::attr(href), h3 a::attr(href)'
        ).getall()

        for link in links:
            if not link:
                continue

            full_url = response.urljoin(link)

            if 'elnuevodiario.com.do' not in full_url:
                continue

            # Extract path and filter sections/categories
            path = full_url.replace('https://elnuevodiario.com.do/', '').strip('/')
            if not path or path in self.section_paths:
                continue
            # Filter pagination, tags, author pages
            if any(x in path for x in ['page/', '/author/', '/tag/', '/wp-', '?']):
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

        # Author
        author = article_data.get('author')
        if isinstance(author, dict):
            author = author.get('name')
        elif isinstance(author, list) and author:
            author = author[0].get('name') if isinstance(author[0], dict) else str(author[0])
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
            paragraphs = response.css('.post-content p::text, .post-content p *::text').getall()
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
            or response.css('.breadcrumb a::text').getall()[-1:]
            or None
        )
        if isinstance(item['category'], list):
            item['category'] = item['category'][0] if item['category'] else None

        # Tags
        tags = response.css('meta[property="article:tag"]::attr(content)').getall()
        if not tags:
            tags = response.css('a[rel="tag"]::text').getall()
        item['tags'] = tags

        # Image
        item['image_url'] = (
            response.css('meta[property="og:image"]::attr(content)').get()
            or response.css('.entry-content img::attr(src)').get()
        )

        item['source'] = 'El Nuevo Diario'

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
                # WordPress often nests in @graph
                if isinstance(data, dict) and '@graph' in data:
                    for d in data['@graph']:
                        if isinstance(d, dict) and d.get('@type') in ('NewsArticle', 'Article'):
                            return d
            except (json.JSONDecodeError, TypeError):
                continue
        return {}

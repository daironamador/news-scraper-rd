import scrapy
import json
import re
from news_scraper.items import NewsItem


class DiarioLibreSpider(scrapy.Spider):
    """
    Spider configured for Diario Libre (diariolibre.com)
    Dominican newspaper - crawls all sections of the site.
    """

    name = "diariolibre"
    allowed_domains = ["diariolibre.com"]

    # All sections and subsections of the site
    sections = [
        # Cover
        "/",
        "/ultima-hora",
        # Current Affairs
        "/actualidad",
        "/actualidad/nacional",
        "/actualidad/ciudad",
        "/actualidad/educacion",
        "/actualidad/salud",
        "/actualidad/justicia",
        "/actualidad/politica",
        "/actualidad/sucesos",
        "/actualidad/a-fondo",
        "/actualidad/dialogo-libre",
        # Politics
        "/politica",
        "/politica/partidos",
        "/politica/jce",
        "/politica/tse",
        "/politica/congreso-nacional",
        "/politica/gobierno",
        "/politica/nacional",
        "/politica/internacional",
        # World
        "/mundo",
        "/mundo/estados-unidos",
        "/mundo/america-latina",
        "/mundo/haiti",
        "/mundo/espana",
        "/mundo/europa",
        "/mundo/canada",
        "/mundo/medio-oriente",
        "/mundo/asia",
        "/mundo/africa",
        # Economy
        "/economia",
        "/economia/finanzas",
        "/economia/turismo",
        "/economia/agro",
        "/economia/empleo",
        "/economia/negocios",
        "/economia/energia",
        # Sports
        "/deportes",
        "/deportes/baloncesto",
        "/deportes/futbol",
        "/deportes/beisbol",
        "/deportes/motor",
        "/deportes/golf",
        # Magazine
        "/revista",
        # Opinion
        "/opinion",
        # Planet
        "/planeta",
        # USA
        "/usa",
    ]

    start_urls = [
        f"https://www.diariolibre.com{section}" for section in sections
    ]

    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'ROBOTSTXT_OBEY': True,
    }

    # Pattern to detect article URLs (contain a date in the path)
    article_url_pattern = re.compile(r'/\d{4}/\d{2}/\d{2}/')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.seen_urls = set()

    def parse(self, response):
        """Extracts article links from each section"""

        article_links = response.css('a::attr(href)').getall()

        for link in article_links:
            if not link:
                continue

            # Build absolute URL
            full_url = response.urljoin(link)

            # Filter only diariolibre articles with date in URL
            if 'diariolibre.com' not in full_url:
                continue
            if not self.article_url_pattern.search(full_url):
                continue

            # Deduplicate
            if full_url in self.seen_urls:
                continue
            self.seen_urls.add(full_url)

            yield scrapy.Request(full_url, callback=self.parse_article)

        # Pagination: follow "see more" links or numeric pagination
        next_pages = response.css('a.next::attr(href), a[rel="next"]::attr(href), .pagination a::attr(href)').getall()
        for page_link in next_pages:
            page_url = response.urljoin(page_link)
            if page_url not in self.seen_urls:
                self.seen_urls.add(page_url)
                yield scrapy.Request(page_url, callback=self.parse)

    def parse_article(self, response):
        """Extracts data from an individual article"""

        item = NewsItem()

        # Try to extract data from JSON-LD (schema.org) first
        ld_json = response.css('script[type="application/ld+json"]::text').getall()
        article_data = {}
        for block in ld_json:
            try:
                data = json.loads(block)
                if isinstance(data, dict) and data.get('@type') in ('NewsArticle', 'Article'):
                    article_data = data
                    break
                if isinstance(data, list):
                    for d in data:
                        if isinstance(d, dict) and d.get('@type') in ('NewsArticle', 'Article'):
                            article_data = d
                            break
            except (json.JSONDecodeError, TypeError):
                continue

        # Title
        item['title'] = (
            response.css('h1::text').get('').strip()
            or article_data.get('headline')
        )

        # URL
        item['url'] = response.url

        # Author
        author = article_data.get('author')
        if isinstance(author, dict):
            author = author.get('name')
        elif isinstance(author, list) and author:
            author = author[0].get('name') if isinstance(author[0], dict) else str(author[0])
        item['author'] = (
            author
            or response.css('meta[name="ArticleAuthors"]::attr(content)').get()
            or response.css('a[href*="/autor/"]::text').get()
        )

        # Published Date
        item['published_date'] = (
            article_data.get('datePublished')
            or response.css('time::attr(datetime)').get()
        )

        # Content - paragraphs of the article body
        paragraphs = response.css('.detail-body p::text, .detail-body p *::text').getall()
        if not paragraphs:
            paragraphs = response.css('article p::text, article p *::text').getall()
        item['content'] = ' '.join(p.strip() for p in paragraphs if p.strip())

        # Summary
        item['summary'] = (
            article_data.get('description')
            or response.css('meta[property="og:description"]::attr(content)').get()
            or response.css('meta[name="description"]::attr(content)').get()
        )

        # Category (from breadcrumb or URL)
        item['category'] = response.css('.breadcrumb a::text').getall()[-1:] or None
        if isinstance(item['category'], list):
            item['category'] = item['category'][0] if item['category'] else None
        if not item['category']:
            parts = response.url.replace('https://www.diariolibre.com/', '').split('/')
            if len(parts) >= 2:
                item['category'] = parts[0].capitalize()

        # Tags
        item['tags'] = response.css('a[href*="/tags/"]::text').getall()

        # Main Image
        og_image = response.css('meta[property="og:image"]::attr(content)').get()
        ld_image = article_data.get('image')
        if isinstance(ld_image, dict):
            ld_image = ld_image.get('url')
        item['image_url'] = og_image or ld_image

        # Source
        item['source'] = 'Diario Libre'

        # Only return if it has title and content
        if item.get('title') and item.get('content'):
            yield item

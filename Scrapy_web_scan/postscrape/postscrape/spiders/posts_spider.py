import scrapy
from bs4 import BeautifulSoup

class PostsSpider(scrapy.Spider):
    name = "posts"
    start_urls = [
        'https://qamqor.gov.kz/',
        'https://qamqor.gov.kz/criminals',
        'https://qamqor.gov.kz/accident',
        'https://qamqor.gov.kz/alimonies'
    ]

    def parse(self, response):
        page = response.url.split('/')[-1]
        filename = f'qamqor.gov.kz-{page}.html'

        # Use BeautifulSoup to prettify the HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        pretty_html = soup.prettify()

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(pretty_html)

# to get scan of page go to terminal and run " scrapy crawl posts" !!!

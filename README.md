dgscraper
=========

dgscrape is a Python program created to scrape text contents (title, main text content and possibly comments) from (hopefully) any web page without tears.

Dependencies:
    BeautifulSoup (included)
    lxml 3.2.3 (earlier version should also work but it is not tested)
   
Installation:
    python setup.py install

How To Use:
    
    from dgscraper import Scraper
    page = Scraper(html_content)
    # To get the title
    title = page.get_title()
    # To get the main text content
    content = page.get_content()
    # You may also get some comments, if possible
    comments = page.get_comments()
    
Refer to the test_scraper.py for the example

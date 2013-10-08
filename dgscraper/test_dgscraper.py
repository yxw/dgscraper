from dgscraper import Scraper

def test_scraper(input_html):
    page = Scraper(html)
    title = page.get_title()
    comments = page.get_comments()
    content = page.get_content()
    print 'contents:', content
    print 'comments:', comments
    print 'title:', title
    kw = "Apple"
    print 'Find keyword "%s" at %d' % (kw, page.find_keyword(kw))

if __name__ == '__main__':
    import sys
    filename = sys.argv[1]
    with open(filename) as fp:
        html = fp.read()
        test_scraper(html)


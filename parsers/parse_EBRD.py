# -*- coding: UTF-8 -*-
import pandas as pd
import requests
import concurrent.futures
from lxml.html import fromstring
from random import randint

session = requests.Session()
session.headers = {'User-Agent': 'Chrome/102.0.5005.63 Mobile Safari/537.36'}


def ebrd(keywords, start_date, end_date, columns, browser, proxies, proxies_logpass):

    # open search page and input keywords
    browser.get('https://ecepp.ebrd.com/delta/noticeSearchResults.html')
    if start_date and end_date != '':
        browser.find_element_by_xpath("//input[@id='min-date']").send_keys(start_date.replace('.', '/'))
        browser.find_element_by_xpath("//input[@id='max-date']").send_keys((end_date.replace('.', '/')))
    browser.find_element_by_xpath("//*[@id='keyword']").send_keys(keywords)

    # collect links for tenders pages
    urls = []
    while True:
        html_tree_ = fromstring(browser.page_source)
        next_page_button = ''.join(html_tree_.xpath('//a[@class="paginate_button next"]/text()'))
        urls = urls + html_tree_.xpath('//td/a/@href')
        if len(next_page_button) < 1:
            break
        else:
            browser.find_element_by_xpath('//a[@class="paginate_button next"]').click()

    # gather data from HTML pages of tenders
    def parse_data(url):
        link = 'https://ecepp.ebrd.com/delta/' + url
        index_proxy = randint(0, len(proxies) - 1)
        proxy = {"http": f"http://{proxies_logpass}@{proxies[index_proxy]}",
                 "https": f"https://{proxies_logpass}@{proxies[index_proxy]}"}
        html_tree = fromstring(session.get(link, proxies=proxy).content)
        index = 'EBRD: ' + ''.join(html_tree.xpath('//strong[text()="EBRD Project ID:"]/parent::td/'
                                                   'following-sibling::td/text()'))
        name = ''.join(html_tree.xpath('//h1[@class="entry-title"]/text()'))
        country = ''.join(html_tree.xpath('//strong[text()="Country:"]/parent::td/following-sibling::td/text()'))
        agency = ''.join(html_tree.xpath('//strong[text()="Client Name:"]/parent::td/following-sibling::td/text()'))
        category = ''.join(html_tree.xpath('//strong[text()="Business Sector:"]/parent::td/following-sibling::td'
                                           '/text()'))
        price = ''
        currency = ''
        date = ''.join(html_tree.xpath('//strong[text()="Publication Date:"]/parent::td/following-sibling::td/text()'))
        description = ''.join(html_tree.xpath('//strong[text()="Procurement Exercise Description:"]'
                                              '/parent::td/following-sibling::td/text()'))

        return [index, name, link, country, agency, category, date, description, price, currency]

    # launch multithreading (enhances the requests speed up to 10-15 times)
    if len(urls) > 0:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, (len(urls)+1))) as executor:
            gen = executor.map(parse_data, urls)
        return pd.DataFrame(list(gen), columns=columns)
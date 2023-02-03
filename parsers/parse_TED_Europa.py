# -*- coding: UTF-8 -*-
import pandas as pd
import requests
import concurrent.futures
from lxml.html import fromstring
from random import randint
import re

session = requests.Session()
session.headers = {'User-Agent': 'Chrome/102.0.5005.63 Mobile Safari/537.36'}


def ted_europa(keywords, start_date, end_date, customers, columns, browser, proxies, proxies_logpass):

    # open search page and input keywords
    browser.get('https://ted.europa.eu/TED/search/search.do')
    browser.find_element_by_xpath("//input[@id='freeText']").send_keys(keywords)
    if start_date and end_date != '':
        browser.find_element_by_xpath("//input[@id='publicationDateFrom']").send_keys(start_date.replace('.', '/'))
        browser.find_element_by_xpath("//input[@id='publicationDateTo']").send_keys(end_date.replace('.', '/'))
    if len(customers) > 0:
        browser.find_element_by_xpath("//input[@id='officialName']").send_keys(customers)
    browser.find_element_by_xpath("//input[@id='searchScope3']").click()
    browser.find_element_by_xpath("//button[@id='search']").click()

    # collect links for tenders pages
    urls = []
    while True:
        html_tree_ = fromstring(browser.page_source)
        next_page_button = ''.join(html_tree_.xpath('(//a[@class="pagenext-link pagenext-icon no-underline-not-focused"'
                                                    ']/@href)[1]'))
        urls = urls + (html_tree_.xpath('//a[@title="View this notice"]/@href'))
        if len(next_page_button) < 1:
            break
        else:
            browser.get('https://ted.europa.eu/TED/search/' + next_page_button)

    # gather data from HTML pages of tenders
    def parse_data(url):
        link = 'https://ted.europa.eu/' + url
        index_proxy = randint(0, len(proxies) - 1)
        proxy = {"http": f"http://{proxies_logpass}@{proxies[index_proxy]}",
                 "https": f"https://{proxies_logpass}@{proxies[index_proxy]}"}
        try:
            html_tree = fromstring(session.get(link, proxies=proxy, timeout=15).content)
        except (requests.exceptions.Timeout, requests.exceptions.ProxyError):
            return []

        index = 'TED Europa: ' + ''.join(html_tree.xpath('//div[@class="stdoc"][1]/p[2]/text()'))
        name = ''.join(html_tree.xpath('//meta[@name="DCSext.w_notice_title"]/@content'))
        name = re.sub(r'^.*?: ', '', name)
        country = ''.join(html_tree.xpath('//meta[@name="DCSext.w_doc_country"]/@content'))
        if country == "UK":
            country = "GB"
        agency = ''.join((html_tree.xpath('(//span[text()="Name and addresses"]/following-sibling::div/text()[1])[1]'))) \
            .replace('Official name: ', '')
        category = ((''.join(html_tree.xpath('//meta[@name="DCSext.w_doc_CPV"]/@content'))).split(';'))
        date = ''.join(html_tree.xpath('//div[@id="docHeader"]/span[@class="date"]/text()'))
        description = ''.join(html_tree.xpath('(//span[contains(text(), "description") or contains(text(), '
                                              '"Description")]/following-sibling::div/p[2]/text())[1]'))
        price = (''.join((''.join(html_tree.xpath('(//div[@class="mlioccur"]/span[contains(text(), "total value") or '
                                                  'contains (text(), "excluding VAT")]/following-sibling::div['
                                                  '1]/text()[1])[1]'))))).replace(' taken into consideration', '')\
                                                  .replace(' ', '')

        if len(price) > 0:
            price = re.sub(r'.*?:', '', price)
            currency = ''.join(filter(str.isalpha, price))
            try:
                price = float(price[:-3])
            except ValueError:
                price = ''
        else:
            currency = None
        return [index, name, link, country, agency, category, date, description, price, currency]

    # launching of multithreading (enhances the requests speed up to 10-15 times)
    if len(urls) > 0:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(11, (len(urls) + 1))) as executor:
            gen = executor.map(parse_data, urls)
        return pd.DataFrame(list(gen), columns=columns)

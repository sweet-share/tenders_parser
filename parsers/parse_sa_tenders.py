# -*- coding: UTF-8 -*-
import pandas as pd
import requests
import concurrent.futures
from lxml.html import fromstring
from random import randint

session = requests.Session()
session.headers = {'User-Agent': 'Chrome/102.0.5005.63 Mobile Safari/537.36'}


def sa_tenders(keywords, columns, browser, proxies, proxies_logpass):

    # open search page and input keywords
    browser.get('https://www.sa-tenders.co.za/')
    browser.find_element_by_xpath("//input[@name='body_value']").send_keys(keywords)
    browser.find_element_by_xpath("//input[@value='Apply']").click()

    # collect links for tenders pages
    urls = []
    while True:
        html_tree_ = fromstring(browser.page_source)
        urls = urls + html_tree_.xpath('//td[@class="views-field views-field-field-extended-title"]/a/@href')
        if len(''.join(html_tree_.xpath('//a[text()="view next 10 ›"]/@href'))) < 1:
            break
        else:
            browser.find_element_by_xpath('//a[text()="view next 10 ›"]').click()

    # gather data from HTML pages of tenders
    def parse_data(url):
        link = 'https://www.sa-tenders.co.za/' + url
        index_proxy = randint(0, len(proxies) - 1)
        proxy = {"http": f"http://{proxies_logpass}@{proxies[index_proxy]}",
                 "https": f"https://{proxies_logpass}@{proxies[index_proxy]}"}
        html_tree = fromstring(session.get(link, proxies=proxy).content)

        index = 'South Africa Tenders: ' + ''.join(html_tree.xpath('(//div[@class="field-item even"]/text())[3]'))
        name = ''.join(html_tree.xpath('(//div[@class="field-item even"]/text())[1]'))
        country = 'ZA'
        agency = ''.join(html_tree.xpath('(//div[@class="field-item even"]/text())[2]'))
        category = list(html_tree.xpath('//div[@class="field field-name-field-sector field-type-taxonomy-term-reference '
                                        'field-label-above"]/div/div/text()'))
        date = ''.join(html_tree.xpath('(//span[@class="date-display-single"]/text())[2]'))
        description = ''.join(html_tree.xpath('(//div[@class="tenderDescription"]//p/text())[1]'))
        if description == '':
            description = ''.join(html_tree.xpath('//span[text()="Description:"]/following-sibling::div/p/text()'))
        price = 0
        currency = 'ZAR'

        return [index, name, link, country, agency, category, date, description, price, currency]

    # launch multithreading (enhances the requests speed up to 10-15 times)
    if len(urls) > 0:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(11, (len(urls)+1))) as executor:
            gen = executor.map(parse_data, urls)
        return pd.DataFrame(list(gen), columns=columns)

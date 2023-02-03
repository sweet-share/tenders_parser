# -*- coding: UTF-8 -*-
from elasticsearch import Elasticsearch
from elasticsearch import helpers
import google_trans_new
import requests
import pandas as pd
import time
import pickle


# plugging to elastic search
def launch_elastic(df, keywords):
    es = Elasticsearch([{'host': 'localhost', 'port': 9200}])
    helpers.bulk(es, create_index(df, keywords))


# creating elasticsearch index
def create_index(df, keywords):
    for index, df_doc in df.iterrows():
        yield {
            '_index': keywords,
            '_id': f"{df_doc['ID']}",
            '_source': {key: df_doc[key] for key in ['ID', 'Наменование закупки', 'Ссылка', 'Страна', 'Заказчик',
                                                     'Категория', 'Дата размещения', 'Переведенный текст', 'Цена',
                                                     'Цена в долларах', 'Валюта']},
        }


# converting currencies to USD
def convert_rates(df):
    response = ((requests.get('https://v6.exchangerate-api.com/v6/c8024224ef1299d11dbe2400/latest/USD')).json())[
        "conversion_rates"]
    df['Курс обмена'] = df['Валюта'].apply(lambda x: response.get(x))
    df['Цена в долларах'] = (df['Цена'] / df['Курс обмена']).fillna(0)
    return df['Цена в долларах']


# text translation into English
def translation(df, proxies, proxies_logpass):
    translated = []
    proxy_index = 0
    proxy = {"https": f"https://{proxies_logpass}@{proxies[proxy_index]}",
             "http": f"http://{proxies_logpass}@{proxies[proxy_index]}"}
    print(proxy)
    translator = google_trans_new.google_translator(proxies=proxy)
    for text in df['Краткое описание'].fillna('No description'):
        try:
            text.replace('©', '').lower().encode('ascii')
            translated.append(text)
        except UnicodeEncodeError:
            try:
                translated.append(translator.translate(text, lang_tgt='en'))
                print(len(translated))
            except google_trans_new.google_trans_new.google_new_transError:
                print('Смена прокси (таймаут)')
                if proxy_index != len(proxies):
                    proxy_index += 1
                else:
                    proxy_index = 0
                proxy = {"https": f"https://{'CyE4gW:Mk8h2S'}@{proxies[proxy_index]}",
                         "http": f"http://{'CyE4gW:Mk8h2S'}@{proxies[proxy_index]}"}
                translator = google_trans_new.google_translator(proxies=proxy)
                time.sleep(0.1)
                translated.append(text)
            except TypeError:
                print('Смена прокси (json)')
                if proxy_index != len(proxies):
                    proxy_index += 1
                else:
                    proxy_index = 0
                proxy = {"https": f"https://{'CyE4gW:Mk8h2S'}@{proxies[proxy_index]}",
                         "http": f"http://{'CyE4gW:Mk8h2S'}@{proxies[proxy_index]}"}
                translator = google_trans_new.google_translator(proxies=proxy)
                time.sleep(10)
                translated.append(text)
    return translated


def prediction(df):
    with open("logreg_model.pkl", 'rb') as file:
        clf, tfidf = pickle.load(file)

    df['Переведенный текст_тех'] = df['Переведенный текст'].str.replace(r"[^\w\s]|[\d]+|(https|http)\S+|_x000d\S+", "",
                                                                        regex=True)
    df['Переведенный текст_тех'] = df['Переведенный текст'].dropna()

    df['Отношение к атомной отрасли'] = clf.predict(tfidf.transform(df['Переведенный текст_тех']).toarray())
    return df['Отношение к атомной отрасли']

# writing data into Excel table
def convert_to_excel(df):
    writer = pd.ExcelWriter(f'Tenders.xlsx', engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Тендеры', index=False)
    workbook = writer.book
    sheet = writer.sheets['Тендеры']
    header_format = workbook.add_format({'text_wrap': True, 'valign': 'vcenter', 'align': 'center',
                                              'fg_color': '#DEEBF7', 'border': 1, 'border_color': '#808080'})
    format_link = workbook.add_format({'valign': 'vcenter', 'text_wrap': True, 'font_color': '#0563C1',
                                       'underline': True})
    format_wr = workbook.add_format({'valign': 'top', 'text_wrap': True})
    sheet.autofilter('A1:M' + str(df.shape[0]))
    sheet.set_default_row(46)
    sheet.set_column('A:A', 10, format_wr)
    sheet.set_column('B:B', 15, format_wr)
    sheet.set_column('C:C', 12, format_wr)
    sheet.set_column('D:D', 9, format_wr)
    sheet.set_column('E:E', 20, format_wr)
    sheet.set_column('F:F', 12, format_wr)
    sheet.set_column('G:G', 12, format_wr)
    sheet.set_column('H:H', 25, format_wr)
    sheet.set_column('I:I', 10, format_wr)
    sheet.set_column('J:J', 8, format_wr)
    sheet.set_column('K:K', 15, format_wr)
    sheet.set_column('L:L', 25, format_wr)
    sheet.set_column('M:M', 11, format_wr)
    for col_num, value in enumerate(df.columns.values):
        sheet.write(0, col_num, value, header_format)
    writer.save()

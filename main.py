# -*- coding: UTF-8 -*-
import datetime as dt
import tkinter as tk
import country_converter as coco
import pandas as pd
from selenium import webdriver
from auxiliary_functions import convert_rates, convert_to_excel, translation, prediction, launch_elastic

from parsers.parse_TED_Europa import ted_europa
from parsers.parse_EBRD import ebrd
from parsers.parse_sa_tenders import sa_tenders


# создание класса интерфейса
class App(tk.Tk):
    def on_push(self):  # функция вызывается нажатием на кнопку "Начать поиск"
        # сбор данных, введенных пользователем в поля
        keywords = self.keywords_entry.get()
        rad_keyword_value = self.rad_keyword.get()
        start_date = self.start_date_entry.get()
        end_date = self.end_date_entry.get()
        customers = self.customers_entry.get()

        # запуск браузера
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('window-size=1920x935')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument("--disable-extensions")
        options.add_argument('--user-agent="Chrome/102.0.5005.63 Mobile Safari/537.36 ')
        options.add_experimental_option("useAutomationExtension", False)
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        browser = webdriver.Chrome(executable_path='chromedriver.exe', options=options)

        # получение прокси и паролей (разделитель - запятая, логин-пароль - первый элемент списка)
        with open("proxies.txt", "r") as file:
            proxies = file.read().split(",")
            proxies_logpass = proxies.pop(0)

        # запуск файлов парсеров и сбор тендеров со всех площадок в одну таблицу
        df = pd.DataFrame(columns=['ID', 'Наменование закупки', 'Ссылка', 'Страна', 'Заказчик', 'Категория',
                                   'Дата размещения', 'Краткое описание', 'Цена', 'Валюта'])

        df = pd.concat([df, ted_europa(keywords, start_date, end_date, customers, df.columns, browser, proxies,
                                       proxies_logpass)])
        df = pd.concat([df, ebrd(keywords, start_date, end_date, df.columns, browser, proxies, proxies_logpass)])
        df = pd.concat([df, sa_tenders(keywords, df.columns, browser, proxies, proxies_logpass)])

        browser.close()

        # обработка, очистка, перевод и классификация полученных результатов
        df['Страна'] = coco.convert(names=df['Страна'], to='name_short')
        df['Дата размещения'] = pd.to_datetime(df['Дата размещения'], infer_datetime_format=True).dt.date.fillna(0)
        df['Цена в долларах'] = pd.to_numeric(convert_rates(df), downcast="float")
        df['Переведенный текст'] = translation(df, proxies, proxies_logpass)
        df['Отношение к атомной отрасли'] = prediction(df)
        df = df.drop_duplicates(subset=['Краткое описание', 'Заказчик']).drop(columns=['Курс обмена'], axis=1) \
            .drop(columns=['Переведенный текст_тех'], axis=1)
        df = df[df['Отношение к атомной отрасли'] == 1]

        convert_to_excel(df)  # выгрузка результатов в Excel-таблицу
        launch_elastic(df, keywords)  # выгрузка результатов в elasticsearch

    def __init__(self):
        # создание элементов пользовательского интерфейса
        super().__init__()
        self.title("Поиск тендеров")
        self.center_window()
        self.main_frame = tk.Frame(master=self, bd=2)
        self.keywords_label = tk.Label(self.main_frame, text='Ключевые фразы через запятую:')
        self.keywords_entry = tk.Entry(self.main_frame)
        self.customers_label = tk.Label(self.main_frame, text='Заказчики (если требуется):')
        self.customers_entry = tk.Entry(self.main_frame)
        self.rad_keyword = tk.IntVar()
        self.rad_keyword.set(0)
        self.rad_keyword1 = tk.Radiobutton(self.main_frame, text='Все ключевые слова', variable=self.rad_keyword,
                                           value=0)
        self.rad_keyword2 = tk.Radiobutton(self.main_frame, text='Любое из ключевых слов', variable=self.rad_keyword,
                                           value=1)
        self.rad_keyword3 = tk.Radiobutton(self.main_frame, text='Точная фраза', variable=self.rad_keyword, value=2)
        self.date_label = tk.Label(self.main_frame, text='Введите даты публикации')
        self.date_2_label = tk.Label(self.main_frame, text='в формате ДД.ММ.ГГГГ')
        self.start_date_label = tk.Label(self.main_frame, text='с:')
        self.start_date_entry = tk.Entry(self.main_frame)
        self.end_date_label = tk.Label(self.main_frame, text='по:')
        self.end_date_entry = tk.Entry(self.main_frame)
        self.search_button = tk.Button(self, text='Начать поиск', command=self.on_push)
        self.quit_button = tk.Button(self, text='Выйти из программы', command=self.quit)

        # размещение элементов интерфейса в окне
        self.main_frame.grid(column=0, row=0)
        self.keywords_label.grid(column=0, row=0)
        self.keywords_entry.grid(column=1, row=0)
        self.customers_label.grid(column=0, row=1)
        self.customers_entry.grid(column=1, row=1)
        self.rad_keyword1.grid(column=0, row=2)
        self.rad_keyword2.grid(column=1, row=2)
        self.rad_keyword3.grid(column=2, row=2)
        self.date_label.grid(column=0, row=3)
        self.date_2_label.grid(column=1, row=3)
        self.start_date_label.grid(column=0, row=4)
        self.start_date_entry.grid(column=1, row=4)
        self.end_date_label.grid(column=0, row=5)
        self.end_date_entry.grid(column=1, row=5)
        self.search_button.grid(column=0, row=6, sticky='WESN')
        self.quit_button.grid(column=0, row=7, sticky='WESN')

        self.start_date_entry.insert(0, (dt.date.today() - dt.timedelta(days=7)).strftime('%d.%m.%Y'))
        self.end_date_entry.insert(0, dt.date.today().strftime('%d.%m.%Y'))

    def center_window(self):
        w = 464
        h = 185
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) / 2
        y = (sh - h) / 2
        self.geometry('%dx%d+%d+%d' % (w, h, x, y))


# запуск пользовательского интерфейса и основной функции
if __name__ == '__main__':
    app = App()
    app.mainloop()

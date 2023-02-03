# -*- coding: UTF-8 -*-
import datetime as dt
import tkinter as tk
import country_converter as coco
import pandas as pd

from selenium import webdriver
from fake_useragent import UserAgent

from auxiliary_functions import convert_rates, convert_to_excel, translation, prediction, launch_elastic

from parsers.parse_TED_Europa import ted_europa
from parsers.parse_EBRD import ebrd
from parsers.parse_sa_tenders import sa_tenders


# launch UI class
class App(tk.Tk):
    def on_push(self):
        # receiving keywords from user
        keywords = self.keywords_entry.get()
        rad_keyword_value = self.rad_keyword.get()
        start_date = self.start_date_entry.get()
        end_date = self.end_date_entry.get()
        customers = self.customers_entry.get()

        # launch browser
        options = webdriver.ChromeOptions()
        ua = UserAgent()

        options.add_argument('--headless')
        options.add_argument('window-size=1920x935')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-sandbox')
        options.add_argument('--ignore-certificate-errors')
        options.add_argument(f'--user-agent={ua["google chrome"]}')
        options.add_experimental_option("useAutomationExtension", False)
        options.add_experimental_option("excludeSwitches", ["enable-automation"])

        browser = webdriver.Chrome(executable_path='chromedriver.exe', options=options)

        # receive proxies
        with open("proxies.txt", "r") as file:
            proxies = file.read().split(",")
            proxies_logpass = proxies.pop(0)

        # launching parser scripts
        df = pd.DataFrame(columns=['ID', 'Procurement name', 'Link', 'Country', 'Client', 'Category',
                                   'Publication date', 'Short description', 'Value (national currency)',
                                   'National currency'])

        df = pd.concat([df, ted_europa(keywords, start_date, end_date, customers, df.columns, browser, proxies,
                                       proxies_logpass)])
        df = pd.concat([df, ebrd(keywords, start_date, end_date, df.columns, browser, proxies, proxies_logpass)])
        df = pd.concat([df, sa_tenders(keywords, df.columns, browser, proxies, proxies_logpass)])

        browser.close()

        # process gathered data
        df['Country'] = coco.convert(names=df['Country'], to='name_short')
        df['Publication date'] = pd.to_datetime(df['Publication date'], infer_datetime_format=True).dt.date.fillna(0)
        df['Value (USD)'] = pd.to_numeric(convert_rates(df), downcast="float")
        df['Translated text'] = translation(df, proxies, proxies_logpass)
        df['Relation to nuclear sphere'] = prediction(df)
        df = df.drop_duplicates(subset=['Short description', 'Client']).drop(columns=['Exchange rate'], axis=1) \
            .drop(columns=['Translated text_temp'], axis=1)
        df = df[df['Relation to nuclear sphere'] == 1]

        convert_to_excel(df)  # write results into Excel
        launch_elastic(df, keywords)  # write results into elasticsearch DB

    def __init__(self):
        # UI elements
        super().__init__()
        self.title("Tender search")
        self.center_window()
        self.main_frame = tk.Frame(master=self, bd=2)
        self.keywords_label = tk.Label(self.main_frame, text='Keywords:')
        self.keywords_entry = tk.Entry(self.main_frame)
        self.customers_label = tk.Label(self.main_frame, text='Tender announcer (if required):')
        self.customers_entry = tk.Entry(self.main_frame)
        self.rad_keyword = tk.IntVar()
        self.rad_keyword.set(0)
        self.rad_keyword1 = tk.Radiobutton(self.main_frame, text='All keywords', variable=self.rad_keyword,
                                           value=0)
        self.rad_keyword2 = tk.Radiobutton(self.main_frame, text='Any keyword', variable=self.rad_keyword,
                                           value=1)
        self.rad_keyword3 = tk.Radiobutton(self.main_frame, text='Exact query', variable=self.rad_keyword, value=2)
        self.date_label = tk.Label(self.main_frame, text='Publication date')
        self.date_2_label = tk.Label(self.main_frame, text='in DD.MM.YYYY')
        self.start_date_label = tk.Label(self.main_frame, text='from:')
        self.start_date_entry = tk.Entry(self.main_frame)
        self.end_date_label = tk.Label(self.main_frame, text='to:')
        self.end_date_entry = tk.Entry(self.main_frame)
        self.search_button = tk.Button(self, text='Launch', command=self.on_push)
        self.quit_button = tk.Button(self, text='Exit', command=self.quit)

        # UI window parameters
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
        w = 386
        h = 185
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) / 2
        y = (sh - h) / 2
        self.geometry('%dx%d+%d+%d' % (w, h, x, y))


# launching UI and main function
if __name__ == '__main__':
    app = App()
    app.mainloop()

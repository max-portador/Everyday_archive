import os.path as path
from mechanize import Browser
from bs4 import BeautifulSoup
import datetime as dt
import json
import xlsxwriter as xl

def get_dates_list(start_year, end_year):
    start = dt.datetime.strptime(f"01-01-{start_year}", "%d-%m-%Y")
    end = dt.datetime.strptime(f"31-12-{end_year}", "%d-%m-%Y")
    return [ start + dt.timedelta(days=x) for x in range(0, (end-start).days)]


headers = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) ' \
          'Chrome/79.0.3945.136 YaBrowser/20.2.2.261 Yowser/2.5 Safari/537.36'

stations_list_filename: str = 'station_ids full.json'

# Создаем браузер и настраиваем
def create_browser():
    br = Browser()
    br.set_handle_robots(False)
    br.addheaders = [('user-agent', headers)]
    return br


def get_stations(region_name: str):
    with open(stations_list_filename, 'r') as file:
        data: {} = json.load(file)
        region_stations_ids = data[region_name].values()
        return list(region_stations_ids)


def parse_html_cells(cells):
    meteo_data = {}

    def get_cell_text(number):
        return float(cells[number].text) if cells[number].text != '' else 'Н/Д'

    meteo_data['av_temp'] = get_cell_text(3)
    meteo_data['min_temp'] = get_cell_text(6)
    meteo_data['max_temp'] = get_cell_text(7)
    meteo_data['wind'] = get_cell_text(12)
    meteo_data['gusts'] = get_cell_text(13)
    meteo_data['sum_prep'] = get_cell_text(26)
    meteo_data['max_pressure'] = get_cell_text(18)
    try:
        max_snow = int(float(cells[27].text))
    except ValueError:
        max_snow = ''

    meteo_data['max_snow'] = max_snow

    return meteo_data


class MeteoArchiveLoaderOneList:
    def __init__(self, region, start_year, end_year, save_dir, ids_list=[]):
        self.dates_list =  get_dates_list(start_year, end_year)
        self.browser = create_browser()
        self.stations_ids_list = get_stations(region) if region else ids_list
        self.years = list(map(str, range(start_year, end_year + 1)))

        self.start_year = start_year
        self.end_year = end_year
        self.username = 'ncuksods'
        self.password = 'ncuksods'
        self.save_dir = save_dir

        self.data = {}
        self.station_name = ''

    def login(self):
        self.browser.form = list(self.browser.forms())[0]
        self.browser["username"] = self.username
        self.browser["password"] = self.password
        self.browser.submit()

    def load_single_station_data(self, station_id):
        self.station_name = ''
        for y in self.years:
            html = self.browser.open(f'http://www.pogodaiklimat.ru/summary.php?m=&y={y}&id={station_id}')
            self.parse_html(html)

    def parse_html(self, html):
        soup = BeautifulSoup(html, "lxml")
        # Находим все строки таблицы с данными
        table_rows = soup.find_all('tr')[2:]
        # проходимся по каждой строке
        for row in table_rows:
            row_date = row.find_all('td')[2].text
            self.data.setdefault(row_date, {})
            # получаем все ячейки в строке
            cells = row.find_all('td')
            if self.station_name == "":
                self.station_name = cells[1].text

            if len(cells) > 43:
                self.data[row_date] = parse_html_cells(cells)

    def load_data(self):
        for station_id in self.stations_ids_list:
            try:
                self.browser.open("http://www.pogodaiklimat.ru/login.php")
                self.login()

            except Exception as e:
                print(f"[!]Critical, could not open page. {e}")

            self.load_single_station_data(station_id)
            # print(self.data)
            self.save_data()
            self.data = {}

    def save_data(self):
        save_file_name = path.join(self.save_dir, f'{self.station_name}.xlsx')
        print(save_file_name)

        # Создаем книгу Ecxel
        wb = xl.Workbook(save_file_name)
        ws = wb.add_worksheet(self.station_name)


        # Создаем стили ячеек
        merge_format = wb.add_format({'bold': 1, 'align': 'center', 'valign': 'vcenter'})
        merge_format.set_border(style=1)
        
        date_format = wb.add_format({'num_format': 'dd.mm.yyyy', 'bold': 1, 'align': 'center', 'valign': 'vcenter'})
        date_format.set_border(style=1)

        temp_format = wb.add_format({'num_format': '# ##0', 'align': 'center', 'valign': 'vcenter'})
        temp_format.set_border(style=1)

        columns = [
            'Температура',
            'Минимальная температура',
            'Максимальная температура',
            'Ветер',
            'Порывы ветра', 
            'Осадки, мм', 
            'Давление, гПа',
            'Высота снега, см'
            ]
        
        # пишем шапку таблицы
        for i, column in enumerate(["Дата", *columns]):
            ws.write(0, i, column, merge_format)

        def write_data(row, col, key):
            if key in self.data:
                data = self.data.get(key, "Н/Д").values()
            else:
                data = ['Н/Д'] * len(columns)    
            
            print(key, data)
            for i, record in enumerate(data):
                ws.write(row, col + 1 + i, record, temp_format)

        
        # пишем первые столбцы
        row = 1
        for i, dmy in enumerate(self.dates_list):
            ws.write(row + i, 0, dmy, date_format)
            write_data(row + i, 0, dmy.strftime("%d.%m.%Y"))


        print('Архив станции "' + self.station_name + '" успешно записан!')

        # загружаем прогноз с gismeteo
        # url = gm.search_url_by_name(station_name, br)
        # if url:
        #     forecast = gm.get_forcast(url, br)
        #     # начинаем записывать прогноз с gismeteo
        #     if len(forecast.keys()):
        #         row = 1
        #         for key_date in enumerate(date_list):
        #             # берем дату из списка с 01.01 по 31.12 и присоединием текущий год
        #             gen_date = key_date[1] + '.' + str(years[-1])
        #             if gen_date in forecast.keys():
        #                 # если в forecast есть наша сгененрированная дата, пишем эти данные
        #                 ws_temp.write(row, col, forecast[gen_date], temp_format)
        #                 print("Запись прогноза за " + gen_date)
        #             else:
        #                 # если в forecast нет скачанных данных
        #                 ws_temp.write(row, col, "", temp_format)
        #             row += 1
        #         print('Данные станции "' + station_name + '" успешно записаны!')
        # else:
        #     print("Данные прогноза по станции не найдены")
        wb.close()

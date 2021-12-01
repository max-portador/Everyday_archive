import os.path as path
from mechanize import Browser
from bs4 import BeautifulSoup
import datetime as dt
import json
import xlsxwriter as xl

start_date: dt.date = dt.date(2019, 1, 1)
dateList = [(start_date + dt.timedelta(days=x)).strftime("%d.%m") for x in range(365)]


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


class MeteoArchiveLoader:
    def __init__(self, region, start_year, end_year, save_dir):
        self.browser = create_browser()
        self.stations_ids_list = get_stations(region)
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
            self.save_data()
            self.data = {}

    def save_data(self):
        save_file_name = path.join(self.save_dir, f'{self.station_name}.xlsx')
        print(save_file_name)

        # Создаем книгу Ecxel
        wb = xl.Workbook(save_file_name)
        ws_temp = wb.add_worksheet('Температура')
        ws_mintemp = wb.add_worksheet('Минимальная температура')
        ws_maxtemp = wb.add_worksheet('Максимальная температура')
        ws_wind = wb.add_worksheet('Скорость ветра')
        ws_gust = wb.add_worksheet('Порывы ветра')
        ws_prep = wb.add_worksheet('Осадки, мм')
        ws_pres = wb.add_worksheet('Давление, гПа')
        ws_snow = wb.add_worksheet('Высота снега, см')

        # Создаем стили ячеек
        merge_format = wb.add_format({'bold': 1, 'align': 'center', 'valign': 'vcenter'})
        merge_format.set_border(style=1)

        temp_format = wb.add_format({'num_format': '# ##0', 'align': 'center', 'valign': 'vcenter'})
        temp_format.set_border(style=1)

        # пишем шапки таблиц
        for column in range(len(self.years)):
            for worksheet in wb.worksheets():
                worksheet.write(0, 1 + column, int(self.years[column]), merge_format)

        # пишем первые столбцы
        row = 1
        for i, day_month in enumerate(dateList):
            for worksheet in wb.worksheets():
                worksheet.write(row + i, 0, day_month, merge_format)

        start_col = 1
        for col_id, year in enumerate(self.years):
            # начинаем запись каждого столбца с 1 строки
            start_row = 1
            for row_id, key_date in enumerate(dateList):
                # берем дату из списка с 01.01 по 31.12 и присоединием текущий год
                gen_date = f'{key_date}.{year}'
                print('Запись данных за ' + gen_date)

                if gen_date in self.data.keys():
                    single_date_info = self.data[gen_date]

                    # если в data есть наша сгененрированная дата, пишем эти данные
                    def write_data(_worksheet, key):
                        _worksheet.write(row_id + start_row, col_id + start_col, single_date_info.get(key, "Н/Д"), temp_format)

                    write_data(ws_temp, 'av_temp')
                    write_data(ws_mintemp, 'min_temp')
                    write_data(ws_maxtemp, 'max_temp')
                    write_data(ws_wind, 'wind')
                    write_data(ws_gust, 'gusts')
                    write_data(ws_pres, 'max_pressure')
                    write_data(ws_prep, 'sum_prep')
                    write_data(ws_snow, 'max_snow')

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

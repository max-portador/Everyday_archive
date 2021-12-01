from mechanize import Browser
from bs4 import BeautifulSoup
import json
import statistics as stat
import datetime


def search_url_by_name(station_name, br):
    months_temp_forecast = []
    data = ''
    try:
        data = br.open("https://www.gismeteo.ru/api/v2/search/searchresultforsuggest/{}/?lang=ru&domain=ru".format(convert_to_unicode(station_name))).readline()
    except Exception as e:
        print("[!]Critical, could not open page.")
    result_json = json.loads(data.decode('utf-8'))['items']
    if len(result_json):
        url = result_json[0]['url']
        return url
    else:
        return 0

def convert_to_unicode(name):
    #перекодируем имя станции для url запроса
    return str(name.encode('utf-8')).replace('\\x', '%').upper()[2:-1]

def get_forcast(url, br):
    try:
        html = br.open("https://www.gismeteo.ru" + url + "/month/") #отправляет запрос по url и возвращает html
    except Exception as e:
        print("[!]Critical, could not open page.")
    result = {}
    soup = BeautifulSoup(html, "lxml") #Начинаем парсить html
    div = soup.find('div', {'class' : 'weather-cells'}) #заходим тэги с данными ячеек таблицы с прогнозом
    cell_content = div.findAllNext('div', {'class' : 'cell_content'}) #получаем список тэгов с данными ячейки таблицы
    #создаем генератор дат и получаем строчное представление текущей даты
    nd = next_day_generator()
    check_date = next(nd)
    # Проходимся по списку, по каждой ячейке с данными прогноза
    for cell in cell_content[:31]:
        date = formatter_date(cell.find('div', {'class': 'date'}).text.strip())  #дата прогноза
        #если мы считываем дату, начиная с текущей даты, то начинаем парсить температуру
        if date == check_date[:2]:
            temp = cell.find('div', {'class' : 'temp'})
            unit_celsium_t_list = temp.findAll('span', {'class' : 'value unit unit_temperature_c'}) #находит все тэги с температурой по Цельсию и кладет в список
            temp_max = int(unit_celsium_t_list[0].text.strip().replace("−", '-'))
            temp_min = int(unit_celsium_t_list[1].text.strip().replace("−", '-'))
            result[check_date] = stat.mean([temp_max, temp_min])
            # result[check_date] = temp_max
            print('Загрузил прогноз с gismeteo за '+check_date)

            #обновляем контрольную дату на +1 день
            check_date = next(nd)
    return result

def formatter_date(date):
    if len(date) > 2:        # если в записи есть месяц, например "4 апр", оставляет только число
        date = date[:2].strip()
    if len(date) == 1:
        date = "0" + date  # если дата редставлена однозначным числом, то добавляем в начало '0': '4 становится '04'
    return date


def next_day_generator(count=365):
    #генератор строкового представления дат, начиная с сегодняшнего
    a = datetime.datetime.today()
    for i in range(count):
        yield (a + datetime.timedelta(days=i)).strftime("%d.%m.%Y")



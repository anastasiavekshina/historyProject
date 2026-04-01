
# requests — библиотека для отправки HTTP-запросов к веб-страницам
import requests
# BeautifulSoup — инструмент для парсинга HTML/XML, позволяет искать элементы по тегам, классам, селекторам
from bs4 import BeautifulSoup
# pandas — библиотека для работы с табличными данными (аналог Excel в Python)
import pandas as pd
# matplotlib.pyplot — базовая библиотека для построения графиков и диаграмм
import matplotlib.pyplot as plt
# seaborn — надстройка над matplotlib для более красивых и информативных визуализаций
import seaborn as sns
# Counter — класс из collections для удобного подсчёта частоты элементов (например, тегов)
from collections import Counter
# Словарь с параметрами, которые легко менять без правки основного кода
CONFIG = {
    # Базовый домен сайта (используется для формирования полных ссылок, если в HTML относительные пути)
    "base_url": "https://anastasiavekshina.github.io",
    
    # Полный URL к HTML-странице, которую будем парсить
    # Ваш сайт на GitHub Pages — это один файл, поэтому все данные на одной странице
    "page_url": "https://anastasiavekshina.github.io/historySite/",
    
    # Количество "страниц" для обхода (оставлено для совместимости с исходной логикой)
    # В данном случае не используется, так как весь контент на одной странице с якорями
    "max_pages": 3,
    
    # Задержка между запросами в секундах (этика парсинга, чтобы не нагружать сервер)
    # Здесь можно поставить мало, так как запрос всего один
    "delay": 0.5,
    
    # Имя файла, куда сохраним собранные данные в формате CSV (открывается в Excel)
    "output_csv": "./csv_data/dv_lifestyle_articles.csv",
    
    # Имена файлов для сохранения графиков (изображения в формате PNG)
    "output_plot_monthly": "./diagrams/dv_lifestyle_monthly.png",      # график по месяцам
    "output_plot_authors": "./diagrams/dv_lifestyle_authors.png",      # график по авторам
    "output_plot_tags": "./diagrams/dv_lifestyle_tags.png",            # график по тегам/регионам
    "output_plot_region_themes": "./diagrams/region_themes_stacked.png",  # 4. Тематическое распределение по регионам
    "output_plot_author_activity": "./diagrams/author_activity_heatmap.png",  # 5. Тепловая карта активности авторов
    "output_plot_regions_pie": "./diagrams/regions_pie.png",  # 6. Распределение по регионам
    "output_plot_themes_pie": "./diagrams/themes_pie.png",   # 7. Распределение по темам
    "output_plot_publication_trend": "./diagrams/publication_trend.png",  # 8. Тренд публикаций во времени
    
    # Заголовки HTTP-запроса — имитируем обычный браузер, чтобы сайт не блокировал запрос
    "headers": {
        # User-Agent сообщает серверу, что запрос идёт от браузера Chrome на Windows
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        # Предпочитаемый язык ответа — русский
        "Accept-Language": "ru-RU,ru;q=0.9",
    },
}


# Словарь с CSS-селекторами, которые указывают парсеру, где искать нужные данные в HTML
# Эти селекторы соответствуют классам и тегам в вашем HTML-файле
SELECTORS = {
    # Селектор для поиска ссылок на статьи в списке публикаций
    # Ищем все <a> с классом post-title-link внутри <article> с классом post
    "list_page": {"article_links": "article.post a.post-title-link"},
    
    # Селекторы для извлечения метаданных из полной версии статьи
    "detail_page": {
        "title": "h1.post-title",           # заголовок статьи — тег <h1> с классом post-title
        "date": "time.post-date",           # дата публикации — тег <time> с классом post-date
        "author": "span.post-author",       # автор — тег <span> с классом post-author
        "region": "div.post-tags a:first-child",
        "themes": "div.post-tags a:not(:first-child)",
        "excerpt": "p.post-excerpt",        # краткое описание — тег <p> с классом post-excerpt
        "tags": "div.post-tags a"         # теги — все <a> внутри <div> с классом post-tags
    },
}


# Настраиваем вывод сообщений в консоль: время, уровень важности, текст сообщения

def get_soup(url: str) -> BeautifulSoup | None:
    """
    Отправляет HTTP-запрос к указанному URL и возвращает распарсенный HTML-документ.
    
    Аргументы:
        url (str): адрес веб-страницы для загрузки
    
    Возвращает:
        BeautifulSoup | None: объект для работы с HTML или None при ошибке
    """
    try:
        # Отправляем GET-запрос с заголовками из CONFIG и таймаутом 15 секунд
        resp = requests.get(url, headers=CONFIG["headers"], timeout=15)
        # Если статус ответа не 200 (OK), выбрасываем исключение
        resp.raise_for_status()
        # Явно указываем кодировку UTF-8 для корректного отображения кириллицы
        resp.encoding = "utf-8"
        # Парсим полученный HTML-текст с помощью встроенного парсера html.parser
        return BeautifulSoup(resp.text, "html.parser")
    except requests.RequestException as e:
        # Если произошла сетевая ошибка, записываем её в лог и возвращаем None
        
        return None




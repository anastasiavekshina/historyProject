
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


def extract_all_articles(soup: BeautifulSoup) -> list[dict]:
    """
    Извлекает все статьи из одного HTML-документа.
    
    Особенность: ваш сайт — single-page, где список статей и их полное содержание
    находятся на одной странице, а переходы реализованы через якорные ссылки (#article-1).
    Поэтому мы не делаем отдельные запросы к каждой статье, а ищем их блоки внутри того же soup.
    
    Аргументы:
        soup (BeautifulSoup): распарсенный HTML-документ всей страницы
    
    Возвращает:
        list[dict]: список словарей, где каждый словарь — данные одной статьи
    """
    articles = []           # Список для накопления данных всех статей
    seen_urls = set()       # Множество для отслеживания уже обработанных URL (защита от дублей)

    # Находим все элементы-ссылки на статьи в списке публикаций по селектору из CONFIG
    link_elements = soup.select(SELECTORS["list_page"]["article_links"])

    # Проходим по каждой найденной ссылке
    for link in link_elements:
        # Получаем значение атрибута href (ссылка на статью)
        href = link.get("href", "")
        # Пропускаем ссылки, которые пустые или не ведут на якорь статьи (#article-...)
        if not href or not href.startswith("#article-"):
            continue

        # Формируем полный "виртуальный" URL статьи: базовый адрес + якорь
        # Это нужно для уникальной идентификации статьи в данных
        article_url = f"{CONFIG['page_url']}{href}"
        # Если статья с таким URL уже обработана — пропускаем (дедупликация)
        if article_url in seen_urls:
            continue
        seen_urls.add(article_url)

        # Извлекаем ID статьи из якоря: "#article-1" → "article-1"
        article_id = href.replace("#", "")
        # Ищем в документе блок с полным содержанием статьи по этому ID
        detail_section = soup.find(id=article_id)

        # Если блок с деталями не найден — записываем предупреждение и переходим к следующей
        if not detail_section:
            
            continue

        # Создаём новый BeautifulSoup-объект только для блока с деталями статьи
        # Это нужно, чтобы селекторы искали элементы внутри этой статьи, а не во всём документе
        detail_soup = BeautifulSoup(str(detail_section), "html.parser")

        # Вспомогательные функции для безопасного извлечения текста
        def safe_text(sel: str) -> str | None:
            """
            Возвращает текст первого найденного элемента по селектору, или None если не найдено.
            
            Аргументы:
                sel (str): CSS-селектор для поиска элемента
            
            Возвращает:
                str | None: очищенный от пробелов текст или None
            """
            el = detail_soup.select_one(sel)  # Ищем один элемент по селектору
            return el.get_text(strip=True) if el else None  # Если найдено — возвращаем текст, иначе None

        def safe_list(sel: str) -> list[str]:
            """
            Возвращает список текстов всех найденных элементов по селектору.

            Аргументы:
                sel (str): CSS-селектор для поиска элементов

            Возвращает:
                list[str]: список непустых текстовых значений
            """
            els = detail_soup.select(sel)
            return [el.get_text(strip=True) for el in els if el.get_text(strip=True)]

        # Пытаемся взять краткое описание (эксперт) из превью в списке статей
        # Это резервный вариант: если в полной версии статьи нет excerpt, возьмём из списка
        preview = link.find_parent("article.post")  # Находим родительский <article> для ссылки
        excerpt = None
        if preview:  # Если родитель найден
            exc_el = preview.select_one("p.post-excerpt")  # Ищем элемент с кратким описанием
            if exc_el:  # Если элемент найден
                excerpt = exc_el.get_text(strip=True)  # Сохраняем его текст

        # Теги (источник для региона/тем)
        tags_list = safe_list(SELECTORS["detail_page"]["tags"])
        region = safe_text(SELECTORS["detail_page"]["region"]) or (tags_list[0] if tags_list else None)
        themes_list = safe_list(SELECTORS["detail_page"]["themes"]) or (tags_list[1:] if len(tags_list) > 1 else [])

        # Формируем словарь с данными статьи — структура, которая попадёт в CSV
        article_data = {
            "url": article_url,  # Виртуальный адрес статьи
            "title": safe_text(SELECTORS["detail_page"]["title"]),  # Заголовок
            "publish_date": safe_text(SELECTORS["detail_page"]["date"]),  # Дата публикации
            "author": safe_text(SELECTORS["detail_page"]["author"]),  # Автор
            "region": region,  # Регион (для новых диаграмм)
            "themes": ", ".join(themes_list) if themes_list else None,  # Темы (для новых диаграмм)
            # Краткое описание: берём из превью, если есть, иначе — из полной версии
            "excerpt": excerpt or safe_text(SELECTORS["detail_page"]["excerpt"]),
            "tags": ", ".join(tags_list) if tags_list else None,  # Теги (через запятую)
        }

        # Добавляем статью в список только если заголовок успешно извлечён (валидация качества)
        if article_data["title"]:
            articles.append(article_data)
            # Записываем в лог успешный парсинг (обрезаем заголовок до 50 символов для краткости)
            

    # Возвращаем список всех собранных статей
    return articles


def run_parser() -> list[dict]:
    """
    Главная функция парсера: выполняет загрузку страницы и извлечение данных.
    
    Возвращает:
        list[dict]: список словарей с данными статей
    """
    # Записываем в лог начало процесса с указанием целевого URL
    
    
    # Загружаем и парсим HTML-страницу через функцию get_soup
    soup = get_soup(CONFIG["page_url"])
    # Если загрузка не удалась (soup is None) — возвращаем пустой список
    if not soup:
        return []

    # Записываем в лог начало извлечения статей
    
    # Вызываем функцию извлечения всех статей из распарсенного документа
    collected = extract_all_articles(soup)
    # Записываем в лог итоговое количество собранных статей
    
    
    # Возвращаем список собранных данных
    return collected

def save_to_csv(data: list[dict]) -> pd.DataFrame:
    """
    Сохраняет список словарей в CSV-файл и возвращает DataFrame для дальнейшей работы.
    
    Аргументы:
        data (list[dict]): список словарей с данными статей
    
    Возвращает:
        pd.DataFrame: таблица с данными для визуализации
    """
    # Если данных нет — записываем предупреждение и возвращаем пустой DataFrame
    if not data:
        
        return pd.DataFrame()

    # Преобразуем список словарей в таблицу pandas (каждый словарь — строка, ключи — колонки)
    df = pd.DataFrame(data)
    # Сохраняем таблицу в CSV-файл:
    # - index=False: не сохранять номера строк как отдельный столбец
    # - encoding="utf-8-sig": кодировка с BOM для корректного открытия кириллицы в Excel
    df.to_csv(CONFIG["output_csv"], index=False, encoding="utf-8-sig")
    # Записываем в лог успешное сохранение с указанием имени файла
    
    # Возвращаем DataFrame для использования в функциях визуализации
    return df


def visualize_by_month(df: pd.DataFrame):
    """
    Строит и сохраняет столбчатую диаграмму: количество статей по месяцам.
    
    Аргументы:
        df (pd.DataFrame): таблица с данными статей
    """
    # Проверка: если таблица пустая или нет колонки с датами — выходим с предупреждением
    if df.empty or "publish_date" not in df.columns:
        
        return

    # Преобразуем строковые даты в объекты datetime:
    # - errors="coerce": невалидные даты превращаются в NaT (Not a Time), а не вызывают ошибку
    df["date_parsed"] = pd.to_datetime(df["publish_date"], errors="coerce")
    # Извлекаем из дат период "месяц" (например, 2024-01, 2024-02)
    df["month"] = df["date_parsed"].dt.to_period("M")
    # Подсчитываем количество статей для каждого месяца и сортируем по времени
    monthly = df["month"].value_counts().sort_index()

    # Если после парсинга дат не осталось валидных значений — выходим с предупреждением
    if monthly.empty:
        
        return

    # Создаём новое окно для графика размером 10x5 дюймов
    plt.figure(figsize=(10, 5))
    # Строим столбчатую диаграмму с помощью seaborn:
    # - x: метки месяцев (преобразованы в строки для отображения)
    # - y: количество статей
    # - palette="viridis": цветовая схема от фиолетового к жёлтому
    sns.barplot(
        x=monthly.index.astype(str), 
        y=monthly.values, 
        hue=monthly.index.astype(str), 
        palette="viridis",
        legend=False 
    )
    
    # Добавляем заголовок с увеличенным и жирным шрифтом
    plt.title(
        "Количество статей о Дальнем Востоке по месяцам", fontsize=14, fontweight="bold"
    )
    # Подписи осей с указанием размера шрифта
    plt.xlabel("Месяц", fontsize=11)
    plt.ylabel("Количество статей", fontsize=11)
    # Поворачиваем подписи месяцев на 45° и выравниваем по правому краю для читаемости
    plt.xticks(rotation=45, ha="right")
    # Добавляем горизонтальную сетку с прозрачностью 0.3 для удобства чтения значений
    plt.grid(axis="y", alpha=0.3)
    # Автоматически подгоняем отступы, чтобы подписи не обрезались
    plt.tight_layout()
    # Сохраняем график в файл с высоким разрешением (300 DPI) и обрезкой лишних полей
    plt.savefig(CONFIG["output_plot_monthly"], dpi=300, bbox_inches="tight")
    # Закрываем окно графика, чтобы освободить память перед следующим
    plt.close()
    # Записываем в лог успешное сохранение
    



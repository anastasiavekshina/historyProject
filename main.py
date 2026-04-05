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
    "output_plot_monthly": "./diagrams/dv_lifestyle_monthly.png",  # график по месяцам
    "output_plot_authors": "./diagrams/dv_lifestyle_authors.png",  # график по авторам
    "output_plot_tags": "./diagrams/dv_lifestyle_tags.png",  # график по тегам/регионам
    "output_plot_region_themes": "./diagrams/region_themes_stacked.png",  # 4. Тематическое распределение по регионам
    "output_plot_author_activity": "./diagrams/author_activity_heatmap.png",  # 5. Тепловая карта активности авторов
    "output_plot_regions_pie": "./diagrams/regions_pie.png",  # 6. Распределение по регионам
    "output_plot_themes_pie": "./diagrams/themes_pie.png",  # 7. Распределение по темам
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
        "title": "h1.post-title",  # заголовок статьи — тег <h1> с классом post-title
        "date": "time.post-date",  # дата публикации — тег <time> с классом post-date
        "author": "span.post-author",  # автор — тег <span> с классом post-author
        "region": "div.post-tags a:first-child",
        "themes": "div.post-tags a:not(:first-child)",
        "excerpt": "p.post-excerpt",  # краткое описание — тег <p> с классом post-excerpt
        "tags": "div.post-tags a",  # теги — все <a> внутри <div> с классом post-tags
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
    except requests.RequestException:
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
    articles = []  # Список для накопления данных всех статей
    seen_urls = (
        set()
    )  # Множество для отслеживания уже обработанных URL (защита от дублей)

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
            return (
                el.get_text(strip=True) if el else None
            )  # Если найдено — возвращаем текст, иначе None

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
        preview = link.find_parent(
            "article.post"
        )  # Находим родительский <article> для ссылки
        excerpt = None
        if preview:  # Если родитель найден
            exc_el = preview.select_one(
                "p.post-excerpt"
            )  # Ищем элемент с кратким описанием
            if exc_el:  # Если элемент найден
                excerpt = exc_el.get_text(strip=True)  # Сохраняем его текст

        # Теги (источник для региона/тем)
        tags_list = safe_list(SELECTORS["detail_page"]["tags"])
        region = safe_text(SELECTORS["detail_page"]["region"]) or (
            tags_list[0] if tags_list else None
        )
        themes_list = safe_list(SELECTORS["detail_page"]["themes"]) or (
            tags_list[1:] if len(tags_list) > 1 else []
        )

        # Формируем словарь с данными статьи — структура, которая попадёт в CSV
        article_data = {
            "url": article_url,  # Виртуальный адрес статьи
            "title": safe_text(SELECTORS["detail_page"]["title"]),  # Заголовок
            "publish_date": safe_text(
                SELECTORS["detail_page"]["date"]
            ),  # Дата публикации
            "author": safe_text(SELECTORS["detail_page"]["author"]),  # Автор
            "region": region,  # Регион (для новых диаграмм)
            "themes": (
                ", ".join(themes_list) if themes_list else None
            ),  # Темы (для новых диаграмм)
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
        legend=False,
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


def visualize_by_author(df: pd.DataFrame):
    """
    Строит и сохраняет горизонтальную диаграмму: топ-5 авторов по количеству статей.

    Аргументы:
        df (pd.DataFrame): таблица с данными статей
    """
    # Проверка на пустую таблицу или отсутствие колонки "author"
    if df.empty or "author" not in df.columns:
        return

    # Подсчитываем частоту упоминания каждого автора, берём топ-5
    author_counts = df["author"].value_counts().head(5)
    # Если авторов нет — выходим
    if author_counts.empty:
        return

    # Создаём окно для графика размером 8x5 дюймов
    plt.figure(figsize=(8, 5))
    # Строим горизонтальную столбчатую диаграмму:
    # - x: количество статей (значения)
    # - y: имена авторов (индексы)
    # - palette="magma": цветовая схема от тёмного к светло-оранжевому
    sns.barplot(
        x=author_counts.values,
        y=author_counts.index,
        hue=author_counts.index,
        palette="magma",
        legend=False,
    )

    # Заголовок и подписи осей
    plt.title("Топ-5 авторов по количеству статей", fontsize=14, fontweight="bold")
    plt.xlabel("Количество статей", fontsize=11)
    plt.ylabel("Автор", fontsize=11)
    # Вертикальная сетка для удобства оценки длины столбцов
    plt.grid(axis="x", alpha=0.3)
    # Подгонка отступов
    plt.tight_layout()
    # Сохранение в файл
    plt.savefig(CONFIG["output_plot_authors"], dpi=300, bbox_inches="tight")
    plt.close()


def visualize_regions_pie(df: pd.DataFrame):
    """Круговая диаграмма: распределение статей по регионам."""
    # Если есть колонка region — используем её (точнее и без хардкода)
    if "region" in df.columns and df["region"].notna().any():
        regions_series = df["region"].dropna().astype(str).str.strip()
        regions_series = regions_series[regions_series != ""]
        region_counts = regions_series.value_counts()
    else:
        # Fallback: извлекаем регионы из tags (старый формат CSV)
        all_regions = []
        for tags_str in df["tags"].dropna():
            tags = [t.strip() for t in str(tags_str).split(",") if t.strip()]
            # Фильтруем только регионы
            regions = [
                t
                for t in tags
                if t
                in [
                    "Камчатка",
                    "Владивосток",
                    "Якутия",
                    "Сахалин",
                    "Хабаровск",
                    "Приморье",
                    "Магадан",
                    "Чукотка",
                    "Амурская область",
                    "Еврейская АО",
                ]
            ]
            all_regions.extend(regions)

        region_counts = pd.Series(Counter(all_regions)).sort_values(ascending=False)

    if region_counts.empty:
        return

    plt.figure(figsize=(8, 8))
    plt.pie(
        region_counts.values,
        labels=region_counts.index,
        autopct="%1.1f%%",
        startangle=90,
        colors=plt.cm.Pastel1(range(len(region_counts))),
    )
    plt.title("Распределение статей по регионам ДВ", fontsize=14, fontweight="bold")
    plt.axis("equal")  # Круглая форма
    plt.savefig(CONFIG["output_plot_regions_pie"], dpi=300, bbox_inches="tight")
    plt.close()


def visualize_publication_trend(df: pd.DataFrame):
    """Линейный график: тренд публикаций во времени."""
    df["date_parsed"] = pd.to_datetime(df["publish_date"], errors="coerce")
    df["month"] = df["date_parsed"].dt.to_period("M")
    monthly = df["month"].value_counts().sort_index()

    plt.figure(figsize=(10, 5))
    plt.plot(
        monthly.index.astype(str),
        monthly.values,
        marker="o",
        linewidth=2,
        markersize=8,
        color="#667eea",
        markerfacecolor="white",
        markeredgewidth=2,
    )
    plt.fill_between(
        monthly.index.astype(str), monthly.values, alpha=0.3, color="#667eea"
    )
    plt.title("Динамика публикаций о Дальнем Востоке", fontsize=14, fontweight="bold")
    plt.xlabel("Месяц", fontsize=11)
    plt.ylabel("Количество статей", fontsize=11)
    plt.xticks(rotation=45, ha="right")
    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(CONFIG["output_plot_publication_trend"], dpi=300, bbox_inches="tight")
    plt.close()


def visualize_themes_pie(df: pd.DataFrame):
    """Круговая диаграмма: распределение по тематикам."""
    theme_keywords = {
        "Еда и кухня": ["Еда", "Рестораны", "Корейская кухня"],
        "Культура и традиции": ["Культура", "Традиции", "Фестивали", "Коренные народы"],
        "Природа и экология": ["Природа", "Экотуризм", "Экология", "Тигры", "Океан"],
        "Город и инфраструктура": ["Город", "Инфраструктура", "Туризм"],
        "Спорт и активный отдых": ["Спорт", "Рыбалка", "Хобби"],
        "Искусство и творчество": ["Искусство", "Музыка", "Фотография", "Развлечения"],
        "Бизнес и технологии": ["Бизнес", "Молодёжь", "Космос", "Промышленность"],
    }

    theme_counts = {theme: 0 for theme in theme_keywords}

    source_col = (
        "themes" if ("themes" in df.columns and df["themes"].notna().any()) else "tags"
    )
    for tags_str in df[source_col].dropna():
        tags = [t.strip() for t in str(tags_str).split(",") if t.strip()]
        for theme, keywords in theme_keywords.items():
            if any(tag in keywords for tag in tags):
                theme_counts[theme] += 1

    # Фильтруем пустые категории
    theme_counts = {k: v for k, v in theme_counts.items() if v > 0}

    plt.figure(figsize=(9, 9))
    plt.pie(
        theme_counts.values(),
        labels=theme_counts.keys(),
        autopct="%1.1f%%",
        startangle=90,
        colors=plt.cm.Set3(range(len(theme_counts))),
    )
    plt.title("Распределение статей по тематикам", fontsize=14, fontweight="bold")
    plt.axis("equal")
    plt.savefig(CONFIG["output_plot_themes_pie"], dpi=300, bbox_inches="tight")
    plt.close()


def visualize_region_themes_stacked(df: pd.DataFrame):
    """Столбчатая диаграмма с накоплением: темы по регионам."""
    # Если есть колонка region — берём список регионов из неё (без хардкода)
    if "region" in df.columns and df["region"].notna().any():
        regions = (
            df["region"]
            .dropna()
            .astype(str)
            .str.strip()
            .loc[lambda s: s != ""]
            .unique()
            .tolist()
        )
        regions = sorted(regions)
    else:
        regions = [
            "Камчатка",
            "Владивосток",
            "Якутия",
            "Сахалин",
            "Хабаровск",
            "Приморье",
            "Магадан",
            "Чукотка",
            "Амурская область",
            "Еврейская АО",
        ]

    theme_keywords = {
        "Природа": ["Природа", "Океан", "Тигры", "Экотуризм"],
        "Еда": ["Еда", "Рестораны", "Корейская кухня"],
        "Культура": ["Культура", "Традиции", "Фестивали"],
        "Город": ["Город", "Туризм", "Инфраструктура"],
        "Другое": ["Спорт", "Бизнес", "Искусство", "Космос", "Фотография"],
    }

    region_theme_counts = {
        region: {theme: 0 for theme in theme_keywords} for region in regions
    }

    source_col = (
        "themes" if ("themes" in df.columns and df["themes"].notna().any()) else "tags"
    )

    for _, row in df.iterrows():
        raw_tags = row.get(source_col)
        tags = [
            t.strip()
            for t in str(raw_tags).split(",")
            if pd.notna(raw_tags) and t.strip()
        ]

        row_region = None
        if "region" in df.columns:
            row_region = row.get("region")
            row_region = str(row_region).strip() if pd.notna(row_region) else None
            if row_region == "":
                row_region = None

        # В новом CSV регион отдельным полем; в старом — он внутри tags
        matched_regions = (
            [row_region] if row_region else [r for r in regions if r in tags]
        )
        for region in matched_regions:
            for theme, keywords in theme_keywords.items():
                if any(tag in keywords for tag in tags):
                    region_theme_counts[region][theme] += 1

    # Фильтруем только регионы со статьями
    regions_with_data = [r for r in regions if sum(region_theme_counts[r].values()) > 0]

    fig, ax = plt.subplots(figsize=(12, 6))
    bottom = [0] * len(regions_with_data)
    colors = plt.cm.Set2(range(len(theme_keywords)))

    for idx, (theme, color) in enumerate(zip(theme_keywords.keys(), colors)):
        values = [region_theme_counts[region][theme] for region in regions_with_data]
        ax.bar(
            regions_with_data,
            values,
            bottom=bottom,
            label=theme,
            color=color,
            alpha=0.8,
        )
        bottom = [b + v for b, v in zip(bottom, values)]

    ax.set_title(
        "Тематическое распределение по регионам", fontsize=14, fontweight="bold"
    )
    ax.set_xlabel("Регион", fontsize=11)
    ax.set_ylabel("Количество статей", fontsize=11)
    ax.legend(title="Тематика")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(CONFIG["output_plot_region_themes"], dpi=300, bbox_inches="tight")
    plt.close()


def visualize_author_activity_heatmap(df: pd.DataFrame):
    """Тепловая карта: активность авторов по месяцам."""
    df["date_parsed"] = pd.to_datetime(df["publish_date"], errors="coerce")
    df["month"] = df["date_parsed"].dt.to_period("M").astype(str)

    pivot = pd.crosstab(df["author"], df["month"])

    plt.figure(figsize=(10, 5))
    sns.heatmap(
        pivot,
        annot=True,
        fmt="d",
        cmap="YlGnBu",
        linewidths=0.5,
        cbar_kws={"label": "Количество статей"},
    )
    plt.title("Активность авторов по месяцам", fontsize=14, fontweight="bold")
    plt.xlabel("Месяц", fontsize=11)
    plt.ylabel("Автор", fontsize=11)
    plt.tight_layout()
    plt.savefig(CONFIG["output_plot_author_activity"], dpi=300, bbox_inches="tight")
    plt.close()


def visualize_by_tags(df: pd.DataFrame, top_n: int = 10):
    """
    Строит и сохраняет горизонтальную диаграмму: топ тегов/регионов по частоте упоминания.

    Аргументы:
        df (pd.DataFrame): таблица с данными статей
        top_n (int): сколько топовых тегов показать (по умолчанию 10)
    """
    # Проверка на пустую таблицу или отсутствие колонки "tags"
    if df.empty or "tags" not in df.columns:
        return

    # Создаём пустой список для сбора всех тегов из всех статей
    all_tags = []
    # Проходим по всем непустым значениям в колонке "tags"
    for tags_str in df["tags"].dropna():
        # Разбиваем строку тегов по запятой, убираем лишние пробелы, фильтруем пустые
        tags = [t.strip() for t in str(tags_str).split(",") if t.strip()]
        # Добавляем все теги из текущей статьи в общий список
        all_tags.extend(tags)

    # Если после сбора теги остались пустыми — выходим
    if not all_tags:
        return

    # Подсчитываем частоту каждого тега и берём топ-N самых популярных
    tag_counts = Counter(all_tags).most_common(top_n)
    # Разделяем результат на два списка: сами теги и их количества
    tags, counts = zip(*tag_counts)

    # Создаём окно для графика размером 10x6 дюймов
    plt.figure(figsize=(10, 6))
    # Строим горизонтальную столбчатую диаграмму:
    # - теги по оси Y, количества по оси X
    # - цвет каждого столбца берётся из цветовой схемы viridis
    bars = plt.barh(tags, counts, color=plt.cm.viridis(range(len(tags))))

    # Заголовок с динамическим указанием top_n
    plt.title(
        f"Топ-{top_n} тем и регионов в публикациях", fontsize=14, fontweight="bold"
    )
    # Подписи осей
    plt.xlabel("Количество упоминаний", fontsize=11)
    plt.ylabel("Тег / Регион", fontsize=11)
    # Горизонтальная сетка
    plt.grid(axis="x", alpha=0.3)

    # Добавляем текстовые метки со значениями прямо на столбцы для наглядности
    for bar, count in zip(bars, counts):
        plt.text(
            count + 0.1,  # Позиция по X: чуть правее конца столбца
            bar.get_y() + bar.get_height() / 2,  # Позиция по Y: центр столбца
            str(count),  # Текст: количество
            va="center",  # Вертикальное выравнивание по центру
            fontsize=9,  # Размер шрифта
        )

    # Подгонка отступов
    plt.tight_layout()
    # Сохранение в файл
    plt.savefig(CONFIG["output_plot_tags"], dpi=300, bbox_inches="tight")
    plt.close()


# Этот блок выполняется только если файл запущен напрямую (не импортирован как модуль)
if __name__ == "__main__":
    # Записываем в лог старт программы с указанием темы

    # Вызываем главную функцию парсинга и сохраняем результат в переменную
    raw_data = run_parser()

    # Если данные успешно собраны (список не пустой)
    if raw_data:
        # Сохраняем данные в CSV и получаем DataFrame для визуализации
        df = save_to_csv(raw_data)

        # Построение трёх графиков
        visualize_by_month(df)  # 1. Динамика публикаций по месяцам
        visualize_by_author(df)  # 2. Активность авторов
        visualize_by_tags(df)  # 3. Популярность тем и регионов
        visualize_region_themes_stacked(df)  # 4. Тематическое распределение по регионам
        visualize_author_activity_heatmap(df)  # 5. Тепловая карта активности авторов
        visualize_regions_pie(df)  # 6. Распределение по регионам
        visualize_themes_pie(df)  # 7. Распределение по тем
        visualize_publication_trend(df)  # 8. Тренд публикаций во времени

        print("Парсинг и визуализация завершены успешно.")

from bs4 import BeautifulSoup, SoupStrainer
from urllib.parse import urljoin
import requests
import zipfile
import uuid
import re
import os


class Parser:
    """
    Класс, который хранит в себе текущую страницу и последующие вложенные файлы
    :param  url   - это кореная ссылка на сайт
    :param  id    - это id текущей задачи
    :param  necessary_level - это уровень требуемой вложенности

    Коды ответов HTTP : https://developer.mozilla.org/ru/docs/Web/HTTP/Status
    """
    def __init__(self, url:str, necessary_level:int = 1):
        self.url = url
        self.status = 100
        self.storage = {}
        self.current_level = 1
        self.external_files_counter = 0
        self.task_id = str(uuid.uuid4())
        self.necessary_level = necessary_level
        self.task_folder = self.init_task_dir()

    def init_task_dir(self) -> str:
        """
        Создает папку для хранения всех задач, если её нет,
        а также папку текущей задачи, и все ее подпапки для js, css, html, media контента
        :return: Путь до папки текущей задачи
        """

        if not os.path.isdir("storage"):
            os.makedirs("storage")

        self.storage_folder = os.path.join(os.getcwd(), "storage")

        task_folder = os.path.join(self.storage_folder, "task_"+self.task_id)
        if not os.path.isdir(task_folder):
            os.makedirs(task_folder)

        css_folder = os.path.join(task_folder, "css")
        if not os.path.isdir(css_folder):
            os.makedirs(css_folder)

        js_folder = os.path.join(task_folder, "js")
        if not os.path.isdir(js_folder):
            os.makedirs(js_folder)

        html_folder = os.path.join(task_folder, "html")
        if not os.path.isdir(html_folder):
            os.makedirs(html_folder)

        media_folder = os.path.join(task_folder, "media")
        if not os.path.isdir(media_folder):
            os.makedirs(media_folder)

        return task_folder

    def get_status(self) -> int:
        """
        Получить текущий статус операции
        :return:
        """
        return self.status

    def zipdir(self, path):
        """
        Заархивировать директорию
        :param path: директория
        :return:
        """
        zip_filename = self.task_id+'.zip'
        with zipfile.ZipFile(zip_filename, 'w') as zip:
            for root, dirs, files in os.walk(path):
                for file in files:
                    zip.write(os.path.join(root, file)), os.path.relpath(os.path.join(root, file), os.path.join(path,
                                                                                                                 '..'))

        return zip_filename

    def start(self) -> str:
        """
        Начать парсинг self.url
        При вызове этой функции запускаются основные циклы для парсинга
        :return: ссылку для скачивания
        """
        self.status = 102
        print(f"Обработка... Текущий обрабатываемый уровень вложенности {self.current_level}/{self.necessary_level}")
        next_links = self.parse(self.url) # ссылки на следующие страницы (след. уровень вложенности)
        self.current_level += 1
        while self.current_level <= self.necessary_level:
            print(f"Обработка... Текущий обрабатываемый уровень вложенности {self.current_level}/{self.necessary_level}")
            print(f"Количетво обрабатываемых ссылок {len(next_links)}")

            # Ссылки для последующего уровня
            links = []

            # Парсится следующий уровень вложенности
            while next_links:
                links += self.parse(next_links[0])
                next_links.pop(0)
            next_links = links
            self.current_level += 1

        self.status = 200

        # Заархивировать директорию, куда сохранены результаты текущей задачи
        zip_filename = self.zipdir(self.task_folder)

        return zip_filename

    def parse(self, url) -> list:
        """
        Парсит страницу, на которую привела ссылка
        :param url: Ссылка для парсинга
        :return: список всех ссылок, которые есть на странице
        """

        responce = requests.get(url)

        # Получить необработанный контент страницы по url
        raw = responce.text

        # Структура soup со всеми тегами
        soup = BeautifulSoup(raw, features="html.parser")

        # Сохранить весь html
        self.save_html(url, responce, raw)

        # Сохранить весь css
        self.save_css(url, soup)

        # Сохранить весь js
        self.save_js(soup)

        # Сохранить все медиа-файлы
        self.save_media(soup)

        # Создать структуру данных bs с только <a />
        soup_a = BeautifulSoup(raw, parse_only=SoupStrainer('a'), features="html.parser")
        # Получить все ссылки со страницы для парсинга следующей вложенности
        links = []
        for link in soup_a:
            if link.has_attr('href'):
                relative_link = link['href']
                absolute_link = urljoin(self.url, relative_link)
                links.append(absolute_link)

        return links

    def has_forbidden_characters(self, string):
        return set([char for char in ':?*\|/<>"']).intersection(set([char for char in string]))

    def get_filename(self, url, responce):
        if "Content-Disposition" in responce.headers.keys():
            filename = re.findall("filename=(.+)", responce.headers["Content-Disposition"])[0]
        else:
            filename = url.split("/")[-1]
        return filename

    def save_html(self, url, responce, raw)->None:
        """
        Получить html из контента
        :param raw_content: необработанный контент
        :return: None
        """
        filename = self.get_filename(url, responce)
        html_folder = os.path.join(self.task_folder, "html")
        filename = os.path.join(html_folder, filename)

        # Если стили - это ссылка на сторонний сайт (google fonts, к примеру), то задать кастомное название
        if self.has_forbidden_characters(filename):
            filename = os.path.join(html_folder, "external_html_" + str(self.external_files_counter))
            self.external_files_counter += 1

        if filename.split(".")[-1] != ".html":
            filename = filename + ".html"

        with open(filename, 'w', encoding="utf-8") as f:
            f.write(raw)

    def save_css(self, url, soup)->None:
        """
        Получить css из контента
        :param raw_content: необработанный контент
        :return: None
        """
        for link in soup.findAll('link', href=True):

            pattern = re.search(".css", link['href'])
            if pattern is None: continue

            website_css_path = pattern.string
            website_css_filename = re.search(".css", website_css_path).string.split("/")[-1]
            if website_css_filename:
                local_css_folder = os.path.join(self.task_folder, "css")

                # Если стили - это ссылка на сторонний сайт (google fonts, к примеру), то задать кастомное название
                if self.has_forbidden_characters(website_css_filename):
                    local_absolute_css_filename = os.path.join(local_css_folder ,"external_css_" + str(self.external_files_counter))
                    self.external_files_counter+=1
                # Если стили - это ссылка на .css файл
                else:
                    local_absolute_css_filename = os.path.join(local_css_folder, website_css_filename)

                if local_absolute_css_filename.split(".")[-1] != "css":
                    local_absolute_css_filename += ".css"

                with open(local_absolute_css_filename, 'w', encoding="utf-8") as f:
                    if 'http' not in website_css_path: # добавить префикс сайта, если ссылка относительная
                        website_css_path = urljoin(url, website_css_path)
                    response = requests.get(website_css_path)
                    f.write(response.text)

    def save_js(self, soup)->None:
        """
        Получить JS из контента
        :param raw_content: необработанный контент
        :return: None
        """
        link_js = [sc["src"] for sc in soup.find_all("script", src=True)]
        for url in link_js:
            filename = url.split("/")[-1]
            js_folder = os.path.join(self.task_folder, "js")
            filename = os.path.join(js_folder, filename)

            # Если js - это ссылка на сторонний сайт (google fonts, к примеру), то задать кастомное название
            if self.has_forbidden_characters(filename):
                filename = os.path.join(js_folder,"external_js_" + str(self.external_files_counter))
                self.external_files_counter += 1

            if filename.split(".")[-1] != "js":
                filename += ".js"

            with open(filename, 'w', encoding="utf-8") as f:
                if 'http' not in url:
                    url = urljoin(self.url, url)  # добавить префикс сайта, если ссылка относительная
                response = requests.get(url)
                f.write(response.text)

    def save_media(self, soup)->None:
        """
        Получить media (jpg, png, gif) из контента
        :param soup - структура парсера BeautifulSoap
        :return: None
        """
        img_tags = soup.find_all('img')
        urls = []
        for img in img_tags:
            try:
                urls.append(img['src'])
            except:
                pass
        # urls = [img['src'] for img in img_tags]
        for url in urls:
            pattern = re.search(r'\.(?:jpg|gif|png|jpeg)$', url)
            if pattern is None: continue
            fn = pattern.string.split("/")[-1]
            media_folder = os.path.join(self.task_folder, "media")
            filename = os.path.join(media_folder, fn)
            if self.has_forbidden_characters(filename):
                filename = os.path.join(media_folder, "external_media_" + str(self.external_files_counter))
                self.external_files_counter += 1

            extention = "."+pattern.string.split(".")[-1]

            if filename.split(".")[-1] != extention:
                filename += extention

            with open(filename, 'wb') as f:
                if 'http' not in url:
                    url = urljoin(self.url, url)  # добавить префикс сайта, если ссылка относительная
                response = requests.get(url)
                f.write(response.content)


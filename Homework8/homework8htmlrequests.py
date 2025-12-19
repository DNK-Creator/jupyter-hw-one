from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
import os
from requests import get, put
import urllib.parse
import json
import html


def get_uploaded_files():
    """Возвращает множество имен файлов, уже загруженных на Яндекс Диск"""
    token = "AQAAAABhXZDvAADLW6MdwYMiPkaWvuUYwMMxSk0" # вынесем в отдельную переменную для удобства токен
    url = "https://cloud-api.yandex.net/v1/disk/resources"
    uploaded_files = set() # создаем пустое множество
    offset = 0
    limit = 1000

    while True: # в случае, если не за один запрос загружаются данные
        params = {
            "path": "disk:/Backup",
            "limit": limit,
            "offset": offset
        }
        resp = get(url, headers={"Authorization": f"OAuth {token}"}, params=params)
        
        if resp.status_code != 200:
            # если ошибка, то возвращаем пустой список
            break
            
        data = resp.json() # достаем json из возвращенного ответа на запрос
        if "_embedded" not in data:
            break
            
        items = data["_embedded"]["items"] # находим в атрибутах нужный тип
        for item in items:
            if item["type"] == "file":
                uploaded_files.add(item["name"])
        
        total = data["_embedded"]["total"]
        offset += len(items)
        if offset >= total:
            break
    
    return uploaded_files


def run(handler_class=BaseHTTPRequestHandler):
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, handler_class)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()


class HttpGetHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Обработка get запроса: отображение списка файлов с подсветкой загруженных"""
        # получаем список файлов на диске
        try:
            uploaded_files = get_uploaded_files()
        except Exception as e:
            # в случае ошибки при запросе к API показываем все файлы без подсветки
            print(f"Ошибка при получении списка файлов с Яндекс Диска: {e}")
            uploaded_files = set()

        # формируем HTML-список файлов
        def fname2html(fname):
            # проверяем, загружен ли файл
            style = ' style="background-color: rgba(0, 200, 0, 0.25);"' if fname in uploaded_files else ''
            
            # экранируем имя файла для безопасной вставки в HTML и JSON
            escaped_fname = html.escape(fname)
            json_fname = json.dumps({'filename': fname})
            
            return f"""
                <li onclick="fetch('/upload', {{
                    'method': 'POST',
                    'headers': {{'Content-Type': 'application/json'}},
                    'body': {json_fname}
                }})"{style}>
                    {escaped_fname}
                </li>
            """

        # отправляем HTML-страницу
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        
        files_html = "\n".join(map(fname2html, os.listdir("pdfs")))
        html_content = f"""
            <html>
                <head>
                    <title>Файлы для загрузки</title>
                </head>
                <body>
                    <h1>Файлы в папке pdfs:</h1>
                    <p>Зеленым цветом выделены уже загруженные файлы</p>
                    <ul>
                        {files_html}
                    </ul>
                </body>
            </html>
        """
        self.wfile.write(html_content.encode())

    def do_POST(self):
        """Обработка POST-запроса: загрузка файла на Яндекс Диск"""
        token = "AQAAAABhXZDvAADLW6MdwYMiPkaWvuUYwMMxSk0" # вынесем в отдельную переменную для удобства токен
        content_len = int(self.headers.get('Content-Length'))
        
        # читаем и парсим JSON данные
        try:
            data = json.loads(self.rfile.read(content_len).decode("utf-8"))
            fname = data['filename']
        except (json.JSONDecodeError, KeyError):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Invalid JSON data")
            return

        local_path = f"pdfs/{fname}"
        ya_path = f"Backup/{urllib.parse.quote(fname)}"
        
        # получаем URL для загрузки
        resp = get(f"https://cloud-api.yandex.net/v1/disk/resources/upload?path={ya_path}",
                   headers={"Authorization": f"OAuth {token}"})
        
        if resp.status_code != 200:
            self.send_response(resp.status_code)
            self.end_headers()
            return
            
        upload_url = json.loads(resp.text)["href"]
        
        # загружаем файл
        with open(local_path, 'rb') as f:
            resp = put(upload_url, files={'file': (fname, f)})
        
        # возвращаем результат
        self.send_response(resp.status_code)
        self.end_headers()


run(handler_class=HttpGetHandler)
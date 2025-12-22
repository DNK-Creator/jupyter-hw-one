from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
import os
from requests import get, put
import getpass

PDF_DIR = "pdfs"
BACKUP_DIR = "Backup"


def get_uploaded_files(token):
    """Возвращает множество имён файлов, уже загруженных на Яндекс.Диск (папка BACKUP).
    Реализован постраничный обход (offset/limit) — если файлов много, делается несколько запросов.
    Если токен не задан или произошла ошибка — возвращает пустое множество.
    """
    if not token:
        return set()

    url = "https://cloud-api.yandex.net/v1/disk/resources"
    uploaded = set()
    offset = 0
    limit = 1000
    headers = {"Authorization": f"OAuth {token}"}

    while True:
        params = {
            "path": f"disk:/{BACKUP_DIR}",
            "limit": limit,
            "offset": offset,
        }
        try:
            resp = get(url, headers=headers, params=params, timeout=10)
        except Exception:
            # в случае сетевых ошибок вернём то, что накопили (или пустое множество)
            break

        if resp.status_code != 200:
            # ошибка, прекращаем обход
            break

        try:
            data = resp.json()
        except Exception:
            break

        if "_embedded" not in data:
            break

        items = data["_embedded"].get("items", [])
        for it in items:
            if it.get("type") == "file" and "name" in it:
                uploaded.add(it["name"])

        total = data["_embedded"].get("total", 0)
        offset += len(items)
        if offset >= total:
            break

    return uploaded


def run(handler_class):
    server_address = ('', 8000)
    # спросим токен у пользователя и не сохраняем его в коде
    print("Введите OAuth-token для Яндекс.Диска (ввод скрыт):")
    token = getpass.getpass()
    if not token:
        print("Токен не введён. Перезапустите сервер и введите токен.")
        return

    # запомним токен в классе обработчике, это безопасно потому что не коммитится в репозиторий
    handler_class.TOKEN = token

    httpd = HTTPServer(server_address, handler_class)
    try:
        print("Server started on port 8000")
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()


class HttpGetHandler(BaseHTTPRequestHandler):
    # сюда при запуске записывается токен
    TOKEN: str | None = None

    def do_GET(self):
        """Отдаёт HTML со списком файлов в папке pdfs.
        Элементы, уже загруженные на Диск, подсвечиваются фоном rgba(0, 200, 0, 0.25).
        """
        # убедимся, что папка pdfs существует
        if not os.path.isdir(PDF_DIR):
            try:
                os.makedirs(PDF_DIR, exist_ok=True)
            except Exception:
                self.send_response(500)
                self.end_headers()
                return

        uploaded = set()
        try:
            uploaded = get_uploaded_files(self.TOKEN)
        except Exception:
            uploaded = set()

        def fname2html(fname):
            style = ' style="background-color: rgba(0, 200, 0, 0.25);"' if fname in uploaded else ''
            # при клике отправляем POST на /upload с телом именем файла
            escaped = html_escape(fname)
            # отправляем файл как простую строку в теле
            body_js = fname.replace("'", "\\'")
            return f"""
                <li onclick="fetch('/upload', {{method: 'POST', body: '{body_js}'}})"{style}>
                    {escaped}
                </li>
            """

        try:
            files = sorted(os.listdir(PDF_DIR))
        except Exception:
            files = []

        files_html = "\n".join(map(fname2html, files))

        html_page = f"""
            <html>
                <head>
                    <meta charset="utf-8">
                </head>
                <body>
                    <ul>
                      {files_html}
                    </ul>
                </body>
            </html>
        """

        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html_page.encode('utf-8'))

    def do_POST(self):
        """Загрузка файла на Яндекс Диск."""
        content_len = int(self.headers.get('Content-Length', 0))
        if content_len <= 0:
            self.send_response(400)
            self.end_headers()
            return

        raw = self.rfile.read(content_len).decode("utf-8")
        # убрать возможные кавычки вокруг (fetch мог отправить строку с кавычками)
        fname = raw.strip().strip('"').strip("'")
        local_path = f"{PDF_DIR}/{fname}"
        if not os.path.isfile(local_path):
            self.send_response(404)
            self.end_headers()
            return

        # подготовим путь на диске; requests сам закодирует параметры
        params = {'path': f'{BACKUP_DIR}/{fname}'}
        # запросим upload-href у API
        resp = get("https://cloud-api.yandex.net/v1/disk/resources/upload",
                   headers={"Authorization": f"OAuth {self.TOKEN}"},
                   params=params)
        
        if resp.status_code != 200:
            # вернём код от Яндекса или 502 если что-то пошло не так
            self.send_response(resp.status_code if isinstance(resp.status_code, int) else 502)
            self.end_headers()
            return

        try:
            upload_url = resp.json()["href"]
        except Exception:
            self.send_response(502)
            self.end_headers()
            return

        # загрузим содержимое файла на полученный upload_url (PUT с телом файла)
        try:
            with open(local_path, 'rb') as f:
                put_resp = put(upload_url, data=f, timeout=120)
        except Exception:
            self.send_response(502)
            self.end_headers()
            return

        # возвращаем код от Яндекса
        self.send_response(put_resp.status_code)
        self.end_headers()


def html_escape(s: str) -> str:
    """Простая экранизация для вставки в HTML."""
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;")
             .replace("'", "&#x27;"))


if __name__ == '__main__':
    run(HttpGetHandler)

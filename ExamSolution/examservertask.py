from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from urllib.parse import urlparse

# указываем текстового файла (типо наша БД)
TASKS_FILE = 'tasks.txt'
# оставляем хост пустым, значит можно слушать все доступные сети
HOST = ''
# указываем порт для локал-хоста
PORT = 8000


class TaskStorage:
    """Класс-обёртка для хранения и сохранения задач."""

    def __init__(self, filename: str):
        self.filename = filename
        self.tasks = []  # список словарей
        self._load()

    def _load(self):
        # проверяем, существует ли путь к файлу
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        # валидация простая, ожидаем список словарей
                        self.tasks = data
                    else:
                        self.tasks = []
            except Exception:
                # при ошибке чтения, начинаем с пустого списка
                self.tasks = []
        else:
            # в ином случае также будет пустой список
            self.tasks = []

    def _save(self):
        # записываем сначала во временный файл, затем переименовываем
        tmp = self.filename + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(self.tasks, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.filename)

    def next_id(self) -> int:
        if not self.tasks:
            return 1
        # найти максимум id и прибавить 1
        try:
            max_id = max(int(t.get('id', 0)) for t in self.tasks)
        except Exception:
            max_id = 0
        return max_id + 1

    def add_task(self, title: str, priority: str) -> dict:
        # подходящий json-чик под нашу структуру из задания
        new_task = {
            'title': title,
            'priority': priority,
            'isDone': False,
            'id': self.next_id()
        }
        self.tasks.append(new_task)
        self._save()
        return new_task

    def list_tasks(self) -> list:
        return self.tasks

    def complete_task(self, tid: int) -> bool:
        for t in self.tasks:
            # приводим id к int для сравнения
            try:
                if int(t.get('id')) == int(tid):
                    t['isDone'] = True
                    self._save()
                    return True
            except Exception:
                # если возникает ошибка, не ломаем ничего, а просто пропускаем
                continue
        return False


# класс, который хранит список, загружает из файла, сохраняет обратно, создает новые задачи и помечает сделанными по запросу
storage = TaskStorage(TASKS_FILE)


class TodoHandler(BaseHTTPRequestHandler):
    def _send_json(self, code: int, obj):
        # автоматически заполянем базовые параметры по типу хедера
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_empty(self, code: int):
        self.send_response(code)
        self.send_header('Content-Length', '0')
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == '/tasks':
            tasks = storage.list_tasks()
            self._send_json(200, tasks)
        else:
            # Неподдерживаемый путь
            self._send_json(404, {'error': 'Not Found'})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # POST по ручке /tasks значит создать задачу
        if path == '/tasks':
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_json(400, {'error': 'Empty body'})
                return
            try:
                raw = self.rfile.read(content_length).decode('utf-8')
                data = json.loads(raw)
            except Exception:
                self._send_json(400, {'error': 'Invalid JSON'})
                return

            title = data.get('title')
            priority = data.get('priority')
            # проверяем, правильно ли заполнена важность задачки
            if not title or not isinstance(title, str):
                self._send_json(400, {'error': 'Field "title" is required and must be a string'})
                return
            if priority not in ('low', 'normal', 'high'):
                self._send_json(400, {'error': 'Field "priority" must be one of: low, normal, high'})
                return

            # если все нормально, добавляем задачку
            task = storage.add_task(title, priority)
            self._send_json(200, task)
            return

        # POST /tasks/<id>/complete значит пометить выполненной
        parts = [p for p in path.split('/') if p]
        # ожидаемая структура именно ['tasks', '<id>', 'complete']
        if len(parts) == 3 and parts[0] == 'tasks' and parts[2] == 'complete':
            tid = parts[1]
            # нет необходимости в теле запроса
            ok = storage.complete_task(int(tid))
            if ok:
                self._send_empty(200)
            else:
                self._send_json(404, {'error': 'Task not found'})
            return

        # Если путь не соответствует
        self._send_json(404, {'error': 'Not Found'})


def run(server_class=HTTPServer, handler_class=TodoHandler):
    server_address = (HOST, PORT)
    httpd = server_class(server_address, handler_class)
    print(f"Starting server on port {PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\nStopping server.')
        httpd.server_close()


if __name__ == '__main__':
    run()

"""Вебзастосунок без фреймворку: HTTP-сервер (порт 3000) + UDP Socket-сервер (порт 5000) + MongoDB."""

import logging
import mimetypes
import os
import socket
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from multiprocessing import Process
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from pymongo import MongoClient
from pymongo.errors import PyMongoError

BASE_DIR = Path(__file__).parent
HTTP_HOST, HTTP_PORT = "0.0.0.0", 3000
SOCKET_HOST = os.getenv("SOCKET_HOST", "localhost")
SOCKET_PORT = 5000
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
BUFFER_SIZE = 1024
STATIC_EXTENSIONS = {".css", ".png", ".jpg", ".jpeg", ".ico", ".svg", ".js"}

ROUTES = {
    "/": "index.html",
    "/index.html": "index.html",
    "/message": "message.html",
    "/message.html": "message.html",
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(processName)s] %(message)s")


class HttpHandler(BaseHTTPRequestHandler):
    """Обробник HTTP-запитів: маршрутизація, статика, форма."""

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ROUTES:
            self.send_html(ROUTES[path])
            return

        static_file = (BASE_DIR / path.lstrip("/")).resolve()
        # Віддаємо лише статичні файли всередині папки застосунку (захист від ../ і від видачі коду)
        if (
            static_file.is_file()
            and static_file.parent == BASE_DIR.resolve()
            and static_file.suffix.lower() in STATIC_EXTENSIONS
        ):
            self.send_static(static_file)
        else:
            self.send_html("error.html", 404)

    def do_POST(self):
        if urlparse(self.path).path != "/message":
            self.send_html("error.html", 404)
            return

        length = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(length)
        send_to_socket_server(data)

        # Після відправки форми повертаємо користувача на головну сторінку
        self.send_response(302)
        self.send_header("Location", "/")
        self.end_headers()

    def send_html(self, filename: str, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write((BASE_DIR / filename).read_bytes())

    def send_static(self, file: Path):
        mime_type, _ = mimetypes.guess_type(file)
        self.send_response(200)
        self.send_header("Content-Type", mime_type or "application/octet-stream")
        self.end_headers()
        self.wfile.write(file.read_bytes())


def send_to_socket_server(data: bytes):
    """Пересилає дані форми на Socket-сервер по UDP."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(data, (SOCKET_HOST, SOCKET_PORT))
    except OSError as e:
        logging.error("Не вдалося надіслати дані на Socket-сервер: %s", e)


def parse_message(data: bytes) -> dict:
    """Перетворює байт-рядок форми на словник у форматі документа MongoDB."""
    form = parse_qs(data.decode("utf-8"))
    return {
        "date": str(datetime.now()),
        "username": form.get("username", [""])[0],
        "message": form.get("message", [""])[0],
    }


def run_http_server():
    server = HTTPServer((HTTP_HOST, HTTP_PORT), HttpHandler)
    logging.info("HTTP-сервер запущено на порту %s", HTTP_PORT)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def run_socket_server():
    collection = MongoClient(MONGO_URI)["messages_db"]["messages"]
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("0.0.0.0", SOCKET_PORT))
        logging.info("Socket-сервер запущено на порту %s", SOCKET_PORT)
        while True:
            data, address = sock.recvfrom(BUFFER_SIZE)
            try:
                document = parse_message(data)
                collection.insert_one(document)
                logging.info("Збережено повідомлення від %s: %s", address, document)
            except (UnicodeDecodeError, PyMongoError) as e:
                logging.error("Помилка обробки повідомлення: %s", e)


if __name__ == "__main__":
    http_process = Process(target=run_http_server, name="HTTP")
    socket_process = Process(target=run_socket_server, name="Socket")
    http_process.start()
    socket_process.start()
    http_process.join()
    socket_process.join()

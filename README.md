# goit-cs-hw-06

Фінальне завдання курсу «Комп'ютерні системи»: вебзастосунок без вебфреймворку, Socket-сервер і MongoDB у Docker.

## Як це працює

- `main.py` запускає два процеси (`multiprocessing.Process`):
  - **HTTP-сервер** (`http.server`, порт **3000**) — маршрути `/` → `index.html`, `/message` → `message.html`, статичні файли `style.css` і `logo.png`, для невідомих адрес — `error.html` зі статусом 404;
  - **Socket-сервер** (UDP, порт **5000**) — отримує дані форми, перетворює байт-рядок на словник і зберігає в MongoDB (база `messages_db`, колекція `messages`).
- Форма на `message.html` відправляє POST на `/message`, HTTP-сервер пересилає дані на Socket-сервер по UDP і перенаправляє на головну сторінку.

Формат документа в MongoDB:

```json
{
  "date": "2026-11-14 19:31:27.016300",
  "username": "krabaton",
  "message": "First message"
}
```

## Запуск

```bash
docker-compose up --build
```

Застосунок: http://localhost:3000

Дані MongoDB зберігаються поза контейнером у volume `mongo_data` (див. `docker-compose.yaml`).

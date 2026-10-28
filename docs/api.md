<<<<<<< HEAD
# REST API «Библиотеки» (v1)

Базовый адрес: `/api/v1` (алиас без версии `/api` тоже работает). Интерактивная
документация: `/docs` (Swagger UI), `/redoc`, схема — `/openapi.json`.
Формат — JSON, кодировка UTF-8. Авторизация — `Authorization: Bearer <access_token>`.

## Единый формат ошибок

```json
{ "detail": "Описание ошибки" }
```

Для 422 дополнительно: `"errors": [{"field": "password", "message": "слишком короткое значение (минимум 8 симв.)"}]`.
Для 500: `"request_id"` для поиска в журнале. Стек вызовов и SQL клиенту не отдаются.

| Код | Когда |
|---|---|
| 400 | некорректный запрос |
| 401 | нет/просрочен токен, неверный логин или пароль |
| 403 | недостаточно прав (не admin) |
| 404 | не найдено **или чужое** (чужие записи библиотеки неотличимы от несуществующих) |
| 409 | конфликт: дубликат, оценка не прочитанной книги |
| 422 | ошибка валидации |
| 429 | превышен лимит запросов (заголовок `Retry-After`) |

## Аутентификация

| Метод | Путь | Доступ | Описание |
|---|---|---|---|
| POST | `/auth/register` | гость | `{username, email, password}` → 201 `{id, username, email, role}`; 409 — имя/email заняты |
| POST | `/auth/login` | гость | `{username, password}` (username или email) → `{access_token, refresh_token, token_type, expires_in}` |
| POST | `/auth/token` | гость | то же в формате OAuth2 password flow (форма) — для кнопки Authorize в Swagger |
| POST | `/auth/refresh` | гость | `{refresh_token}` → новая пара; старый refresh отозван (ротация) |
| POST | `/auth/logout` | гость | `{refresh_token}` → 204; токен отозван. Access-токен не нужен |
| GET | `/auth/me` | user | текущий пользователь |

Валидация: `username` 3–50 (буквы, цифры, `. _ -`), `email` ≤ 254, `password` 8–128.
Роль (`role`) клиентом не задаётся.

## Каталог

| Метод | Путь | Доступ | Описание |
|---|---|---|---|
| GET | `/books` | гость | список; параметры ниже |
| GET | `/books/search` | гость | то же + `smart=true` (умный поиск через LLM) |
| GET | `/books/{id}` | гость | карточка: авторы, жанры, `avg_rating`, `ratings_count`; для вошедшего — `my_status`, `my_rating`, `library_id` |
| POST | `/books` | **admin** | `{title, authors[], genres[], publication_year?, cover_url?, description?}` → 201; 409 — такая книга уже есть |
| GET | `/genres` | гость | список жанров |

Параметры списка: `limit` (1–100, по умолчанию 20), `offset` (≥ 0), `q`, `genre`, `author`,
`year`, `sort` (`relevance` · `title` · `year` · `created`), `order` (`asc` · `desc`).
Ответ: `{items, limit, offset, total}`; у каждой книги для вошедшего пользователя есть
`my_status` и `my_rating`.

## Личная библиотека (user)

| Метод | Путь | Описание |
|---|---|---|
| GET | `/library` | `status`, `sort` (`added` · `title` · `status` · `rating`), `order`, `limit`, `offset` |
| GET | `/library/stats` | `{total, want_to_read, in_progress, read, ratings_count, avg_rating}` |
| POST | `/library` | `{book_id, status?}` → 201; 404 — нет книги; 409 — уже в библиотеке |
| PATCH | `/library/{entry_id}` | `{status}`; чужая запись → 404 |
| DELETE | `/library/{entry_id}` | 204; оценка удаляется, книга каталога остаётся |

Статусы: `want_to_read`, `in_progress`, `read`.

## Оценки

| Метод | Путь | Доступ | Описание |
|---|---|---|---|
| GET | `/books/{id}/rating` | user | моя оценка; 404 — нет |
| POST | `/books/{id}/rating` | user | `{plot, characters, style}` (целые 1–10): 201 — создана, 200 — заменена; 404 — книги нет в библиотеке; 409 — статус не «Прочитано» |
| PATCH | `/books/{id}/rating` | user | частичное изменение критериев (хотя бы один); 404 — оценки ещё нет |
| GET | `/books/{id}/ratings` | гость | все оценки книги (`username`, критерии, итог), с пагинацией |

`total = (plot + characters + style) / 3`, округление до одного знака (например, 9, 9, 8 → 8.7).

## Рекомендации (user)

| Метод | Путь | Описание |
|---|---|---|
| GET | `/recommendations` | `limit`, `offset`. До трёх оценок — `personalized: false`, `message` и популярные книги |
| POST | `/recommendations/feedback` | `{recommendation_id, feedback: "helpful" \| "not_helpful"}` → 201 (впервые) / 200 (обновлено); чужая → 404 |

Элемент: `{id, book, reason, score, signals: {similar_to, genres}, feedback}`.
`reason` — пояснение языковой модели; `null`, если модель недоступна.
Ответ также содержит `personalized`, `ratings_count`, `min_ratings`, `message`, `explanations`.

## Служебные

`GET /health` (также `/api/health`, `/api/v1/health`) — `{"status": "ok"}` или 503, если БД недоступна.
`GET /metrics` — метрики Prometheus (`http_requests_total`, `http_request_duration_seconds`).
Каждый ответ содержит `X-Request-ID`.
=======
# Контракт API «Библиотеки»

Базовый префикс: `/api/`. Формат — JSON (UTF-8). Авторизация — JWT
(`Authorization: Bearer <token>`), выдаётся при регистрации/входе и
живёт `ACCESS_TOKEN_EXPIRE_MINUTES` минут (по умолчанию 60).
Интерактивная документация (Swagger): `http://localhost:8000/docs`.

## Формат ошибок

```json
{ "error": { "code": "validation_error", "message": "..." } }
```

| HTTP | code                  | Когда |
|------|-----------------------|-------|
| 400  | `validation_error`    | Некорректные данные |
| 401  | `unauthorized`        | Нет / просрочен токен |
| 401  | `invalid_credentials` | Неверный логин/пароль |
| 404  | `not_found`           | Ресурс не найден или принадлежит другому пользователю |
| 409  | `conflict`            | Книга уже есть в библиотеке пользователя |
| 422  | `validation_error`    | Ошибка валидации тела запроса, с `details: [{field, message}]` |

## Авторизация — `/api/auth/`

| Метод | Путь             | Доступ    | Описание |
|-------|------------------|-----------|----------|
| POST  | `/auth/register` | публичный | `{ username, email?, password }` → `{ access_token, user }` |
| POST  | `/auth/login`    | публичный | `{ username, password }` → `{ access_token, user }` |
| POST  | `/auth/logout`   | токен     | Для JWT без состояния — токен удаляется на клиенте |
| GET   | `/auth/me`       | токен     | Текущий пользователь |

## Общая база книг — `/api/books` («будущий каталог»)

Отдельного каталога с готовыми книгами нет: база наполняется тем, что
пользователи вводят вручную через форму, и в ней можно искать.

| Метод | Путь            | Доступ | Описание |
|-------|-----------------|--------|----------|
| GET   | `/books`        | токен  | Поиск. Параметры: `q` (название, автор, описание), `limit`, `offset` |
| GET   | `/books/{id}`   | токен  | Карточка книги + `status`/`my_rating` из библиотеки пользователя |
| POST  | `/books`        | токен  | Добавить книгу в общую базу (в интерфейсе не используется — книги создаются через `/library/custom`) |

## Личная библиотека — `/api/library`

| Метод  | Путь                  | Доступ | Описание |
|--------|-----------------------|--------|----------|
| GET    | `/library`            | токен  | Записи пользователя; параметр `status` — фильтр |
| POST   | `/library`            | токен  | `{ book_id, status? }` — добавить найденную через поиск книгу |
| POST   | `/library/custom`     | токен  | **Форма «Добавить книгу»**: `{ title, author, description?, comment? }` — создаёт книгу в общей базе (или берёт существующую с тем же названием и автором) и добавляет в библиотеку со статусом `want_to_read` |
| PATCH  | `/library/{entry_id}` | токен  | `{ status? , comment? }` — сменить статус и/или личный комментарий |
| DELETE | `/library/{entry_id}` | токен  | Убрать книгу из библиотеки (оценка удаляется вместе с записью) |

Каждая запись в ответе содержит `rating` — `{ plot, characters, style, total, ... }` или `null`,
если книга ещё не оценена (`my_rating` дублирует `rating.total`).

Статусы: `want_to_read`, `reading`, `read`.
`description` — краткое описание сюжета (общее для книги), `comment` — личный
комментарий пользователя (виден только ему).

## Оценки — `/api/library/{entry_id}/rating`

| Метод  | Путь                         | Доступ | Описание |
|--------|------------------------------|--------|----------|
| GET    | `/library/{entry_id}/rating` | токен  | Текущая оценка (404, если ещё не выставлена) |
| PUT    | `/library/{entry_id}/rating` | токен  | `{ plot, characters, style }` (1–10) → сохраняет, пересчитывает `total`, ставит статус `read` |
| DELETE | `/library/{entry_id}/rating` | токен  | Удалить оценку |

`total = round((plot + characters + style) / 3, 2)`.

## Прочее

- `GET /api/health` — проверка живости.
>>>>>>> 088ebc434e4e609566051a7126e169906afacece

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

# Библиотека

Личный читательский дневник: своя библиотека книг со статусами чтения,
личными комментариями и многокритериальными оценками. Книги добавляются
через поиск по общей базе либо вручную — через форму.

Учебная работа (университет), к промышленной реализации не готовится —
архитектура намеренно упрощена. Полный контракт API — в [`docs/api.md`](docs/api.md).

## Возможности

- Регистрация, вход, JWT-авторизация.
- **Добавление книги:** строка поиска по общей базе (название / автор / описание)
  либо форма вручную — название, автор, краткое описание сюжета, комментарий.
  Введённые вручную книги попадают в общую базу и находятся поиском
  (задел под будущий каталог).
- Личная библиотека со статусами «хочу прочитать» / «читаю» / «прочитано».
- Личный комментарий к каждой книге (можно править на странице книги).
- Оценка по трём критериям (сюжет, персонажи, стиль) и общая оценка — среднее трёх;
  общая пересчитывается прямо при движении ползунков. Все четыре цифры видны на карточке книги,
  оценить можно кнопкой «Оценить» на карточке или на странице книги.
- Профиль со статистикой чтения.

## Технологии

**Backend:** Python, FastAPI, SQLAlchemy 2.0, Pydantic v2, PostgreSQL
(полнотекстовый поиск), JWT (python-jose), bcrypt.
**Frontend:** React 18, TypeScript, Vite, Redux Toolkit, React Router, Axios.
**Инфраструктура:** Docker Compose, Nginx.

## Запуск через Docker Compose

```bash
copy backend\.env.example backend\.env     # Windows (cmd/PowerShell)
# cp backend/.env.example backend/.env     # Linux/macOS

docker compose up --build
```

- Приложение: <http://localhost:8080>
- Swagger API: <http://localhost:8000/docs>

Таблицы создаются автоматически при старте бэкенда; новая колонка
`user_books.comment` добавляется в существующую базу сама.

**Полный сброс данных** (удалит все аккаунты и книги):

```bash
docker compose down -v
```

## Переменные окружения бэкенда (`backend/.env`)

| Переменная | Назначение | По умолчанию |
|---|---|---|
| `DATABASE_URL` | Подключение к PostgreSQL | в `.env.example` |
| `JWT_SECRET_KEY` | Секрет подписи JWT — смените | dev-ключ |
| `JWT_ALGORITHM` | Алгоритм подписи | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Срок жизни токена | `60` |
| `CORS_ORIGINS` | Разрешённые origin'ы | `http://localhost:5173` |

## Структура

```
backend/app/
  main.py        # FastAPI, CORS, формат ошибок, лёгкая миграция
  models.py      # User, Book, Author, Genre, UserBook (+comment), Rating
  schemas.py     # Pydantic-схемы
  security.py    # bcrypt + JWT
  routers/       # auth, books (поиск), library (+/custom), ratings
frontend/src/
  pages/         # Home, Login, Register, Library, Book, Profile
  components/    # Navbar, BookCard, RatingForm, PrivateRoute
  store/         # Redux Toolkit: auth, library
  styles/        # index.css — палитра и шрифты
```

## Версии

- **v1** — с каталогом и ИИ-рекомендациями (TF-IDF + OpenAI), архив
  `biblioteka_v1_katalog_rekomendacii.zip`.
- **v2 (текущая)** — каталог и рекомендации убраны; добавление через поиск и форму,
  комментарии, оценки на карточках, приглушённая палитра.

## Ограничения (осознанно)

- Нет Alembic: схема создаётся через `create_all` + одна ручная миграция.
- Нет автотестов.
- Общая база книг не модерируется: любой пользователь может добавить книгу,
  и она станет видна другим в поиске.

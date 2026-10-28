# Библиотека

Персональный читательский дневник: каталог книг, личная библиотека со статусами
чтения, оценка по трём критериям (сюжет, персонажи, язык и стиль) с итоговой
оценкой-средним и персональные рекомендации (TF-IDF + косинусное сходство,
пояснения — через внешнюю языковую модель по желанию).

Реализовано по ТЗ «описание_приложения» (версия 3 приложения).

## Быстрый старт

```powershell
copy backend\.env.example backend\.env      # Linux/macOS: cp backend/.env.example backend/.env
docker compose up --build
```

| Что | Адрес |
|---|---|
| Приложение | http://localhost:8080 |
| Swagger UI (только разработка) | http://localhost:8000/docs |
| Проверка работоспособности | http://localhost:8000/health |

Администратор создаётся при первом запуске из `ADMIN_*` в `backend/.env`
(по умолчанию `admin` / `change-me-admin-password` — **смените**). Только admin
может добавлять книги в каталог (страница «Добавить книгу» в меню). Демо-каталог
из 23 книг загружается при `SEED_DEMO_DATA=true`, если таблица книг пуста.

> **Переход с v2.** Схема БД изменилась (ТЗ, раздел 14), а миграции теперь делает
> Alembic. Старые данные несовместимы — выполните `docker compose down -v`
> (удалит том с базой) и запустите заново.

## Что реализовано

- Регистрация, вход, **access JWT (15 мин) + refresh-токен (7 дней)** с ротацией,
  отзывом при выходе и обнаружением повторного использования; пароли — Argon2id.
- Роли `user` / `admin`, проверка прав и владельца записей на сервере.
- Каталог: пагинация (`limit` по умолчанию 20, максимум 100), фильтры (жанр, автор,
  год), сортировка по белому списку, **полнотекстовый поиск PostgreSQL** (GIN-индекс
  по названию, авторам, жанрам, описанию) + подстрочный поиск; «умный поиск» через LLM.
- Личная библиотека: статусы «Хочу прочитать» / «В процессе» / «Прочитано», фильтр, сортировка,
  пагинация, статистика для профиля.
- Оценки: только для статуса «Прочитано», критерии — целые 1–10, итог = среднее
  (пересчёт триггером БД и в приложении), аудит изменений в `rating_audit`.
- Рекомендации: персональные от **3 оценок**, иначе сообщение и «популярное»;
  уже добавленные книги не предлагаются; обратная связь «полезно / не полезно»
  (не полезно — книга больше не показывается); пояснения LLM с сохранением в БД;
  при сбое LLM — подборка без пояснений.
- Redis-кэш (каталог 5 мин, рекомендации 1 час) с обязательным запасным режимом без Redis.
- Rate limiting (100 запросов/мин на IP; 10/мин для входа и регистрации).
- Единый формат ошибок `{"detail": "..."}` (для 422 — ещё `errors`), на русском, без стека.
- `X-Request-ID`, журнал с идентификатором запроса, метрики Prometheus на `/metrics`.
- Alembic-миграции, OpenAPI (Swagger/ReDoc), версионирование API `/api/v1`
  (алиас без версии `/api/...` тоже работает).

## Переменные окружения (`backend/.env`)

| Переменная | Назначение | По умолчанию |
|---|---|---|
| `APP_ENV` | `production` запрещает дефолтный JWT-секрет | `development` |
| `DATABASE_URL` | Подключение к PostgreSQL | в `.env.example` |
| `JWT_SECRET_KEY` | Секрет подписи JWT — **обязательно смените** | dev-ключ |
| `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRE_DAYS` | Сроки токенов | `15` / `7` |
| `CORS_ORIGINS` | Белый список источников через запятую | `http://localhost:5173` |
| `DOCS_ENABLED` | Swagger/ReDoc/openapi.json | `true` |
| `LOG_LEVEL` | Уровень журнала | `INFO` |
| `RATE_LIMIT_ENABLED`, `RATE_LIMIT_DEFAULT`, `RATE_LIMIT_AUTH` | Лимиты запросов в минуту на IP | `true`, `100`, `10` |
| `REDIS_URL` | Адрес Redis; пусто — кэш выключен | — |
| `OPENAI_API_KEY` | Ключ LLM; пусто — пояснения и умный поиск отключены | — |
| `OPENAI_BASE_URL`, `OPENAI_MODEL` | Любой Chat Completions-совместимый API | OpenAI, `gpt-4o-mini` |
| `ADMIN_USERNAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` | Первый администратор | из `.env.example` |
| `SEED_DEMO_DATA` | Демо-каталог при пустой таблице книг | `false` |

## Миграции

Выполняются автоматически при старте backend (`start.sh`). Вручную:

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend alembic downgrade base      # откат всей схемы
```

Схему БД создаёт именно миграция `alembic/versions/0001_initial.py` (DDL из раздела 14 ТЗ
+ таблица `refresh_tokens`), а не `create_all` — ENUM, триггеры и CHECK живут в БД.

## Тесты

Юнит-тесты (чистая логика) идут без БД; интеграционные API-тесты требуют PostgreSQL:

```powershell
docker compose up -d db
docker compose exec db psql -U biblioteka -c "CREATE DATABASE biblioteka_test"
docker compose run --rm --no-deps -e TEST_DATABASE_URL=postgresql+psycopg://biblioteka:biblioteka@db:5432/biblioteka_test backend sh -c "pip install -q -r requirements-dev.txt && pytest --cov=app --cov-report=term-missing"
```

Покрыто: регистрация/вход/refresh/logout, права admin, каталог и поиск (в т.ч. попытки
SQL-инъекций), библиотека и чужие записи, правила оценок (статус «Прочитано», диапазон
1–10, пересчёт итога, триггер БД, аудит), рекомендации (порог 3 оценок, исключения, обратная
связь, сбой LLM), формат ошибок, rate limiting, метрики.

## Нагрузочное тестирование

См. `load/k6-load.js` — сценарии «Каталог, 100 RPS, 10 мин» и «Смешанные запросы» из ТЗ (p95 ≤ 500 мс, ошибки < 1 %). Команды запуска — в шапке скрипта.
На время теста отключите rate limiting (`RATE_LIMIT_ENABLED=false`).

## Структура

```
backend/
  app/
    main.py            # приложение, middleware, роутеры /api/v1 и /api
    config.py, database.py, models.py, schemas.py, security.py, deps.py
    errors.py, validation_messages.py   # единый формат ошибок, перевод на русский
    middleware.py, logging_config.py    # request_id, метрики, журнал
    ratelimit.py, ratelimit_core.py, cache.py
    routers/           # auth, books, library, ratings, recommendations, health
    services/          # books (поиск), ratings, recommender(+engine), llm, bootstrap
  alembic/             # миграции
  tests/               # pytest
frontend/src/          # React + TypeScript + Redux Toolkit
load/k6-load.js        # нагрузочный тест
docs/api.md            # справочник API
```

## Известные упрощения

- Токены хранятся в `localStorage` (удобно для учебного проекта; для production
  безопаснее HttpOnly-cookie для refresh-токена — см. ТЗ, раздел 15.2).
- Access JWT нельзя отозвать мгновенно (он живёт 15 минут); отзывается refresh-токен.
  Роль пользователя при этом читается из БД на каждом запросе, поэтому понижение
  роли действует сразу.
- `/metrics` не защищён паролем, но nginx его наружу не проксирует (доступен только
  внутри docker-сети — для Prometheus).

// Нагрузочный тест (ТЗ 15.5): два сценария из таблицы результатов — «Каталог, 100 RPS, 10 мин»
// и «Смешанные запросы, 100 RPS, 10 мин». Целевые метрики ТЗ: p95 <= 500 мс, ошибки < 1%,
// типовой запрос каталога/поиска — p95 <= 300 мс.
//
// ВАЖНО: ограничение запросов (100/мин на IP) исказит результат — на время теста выставьте в
// backend/.env  RATE_LIMIT_ENABLED=false  и перезапустите backend; после теста верните true.
//
// Запуск (PowerShell, Docker Desktop), SCENARIO = catalog | mixed:
//   Get-Content load\k6-load.js | docker run --rm -i -e SCENARIO=catalog -e BASE_URL=http://host.docker.internal:8080 grafana/k6 run -
//   Get-Content load\k6-load.js | docker run --rm -i -e SCENARIO=mixed   -e BASE_URL=http://host.docker.internal:8080 grafana/k6 run -
// Быстрая проверка:  -e RATE=20 -e DURATION=1m
// CPU/RAM для таблицы: в соседнем окне во время теста — docker stats --no-stream
import http from "k6/http";
import { check } from "k6";

const BASE = `${__ENV.BASE_URL || "http://host.docker.internal:8080"}/api/v1`;
const SCENARIO = __ENV.SCENARIO || "catalog";

export const options = {
  scenarios: {
    load: {
      executor: "constant-arrival-rate", // фиксированный RPS независимо от времени ответа
      rate: Number(__ENV.RATE || 100),
      timeUnit: "1s",
      duration: __ENV.DURATION || "10m",
      preAllocatedVUs: 100,
      maxVUs: 400,
    },
  },
  summaryTrendStats: ["avg", "med", "p(90)", "p(95)", "max"], // med = p50 для таблицы
  thresholds: {
    http_req_duration: ["p(95)<500"],
    "http_req_duration{kind:catalog}": ["p(95)<300"],
    "http_req_duration{kind:search}": ["p(95)<300"],
    http_req_failed: ["rate<0.01"],
  },
};

const JSON_HEADERS = { "Content-Type": "application/json" };
const QUERIES = ["война", "космос", "фэнтези", "детектив", "любовь", "магия", "история", "роман"];

export function setup() {
  const user = { username: "loadtest", email: "loadtest@example.com", password: "LoadTest-12345" };
  http.post(`${BASE}/auth/register`, JSON.stringify(user), { headers: JSON_HEADERS }); // 409, если уже есть
  const login = http.post(
    `${BASE}/auth/login`,
    JSON.stringify({ username: user.username, password: user.password }),
    { headers: JSON_HEADERS }
  );
  const ids = (http.get(`${BASE}/books?limit=50`).json("items") || []).map((b) => b.id);
  return { token: login.json("access_token"), ids };
}

function catalog() {
  const offset = Math.floor(Math.random() * 3) * 20;
  const r = http.get(`${BASE}/books?limit=20&offset=${offset}`, { tags: { kind: "catalog" } });
  check(r, { "каталог: 200": (x) => x.status === 200 });
}

function mixed(data) {
  const auth = { headers: { Authorization: `Bearer ${data.token}` } };
  const roll = Math.random();
  if (roll < 0.4) {
    const q = QUERIES[Math.floor(Math.random() * QUERIES.length)];
    const r = http.get(`${BASE}/books/search?q=${encodeURIComponent(q)}&limit=20`, { tags: { kind: "search" } });
    check(r, { "поиск: 200": (x) => x.status === 200 });
  } else if (roll < 0.65) {
    catalog();
  } else if (roll < 0.8 && data.ids.length) {
    const id = data.ids[Math.floor(Math.random() * data.ids.length)];
    check(http.get(`${BASE}/books/${id}`, { tags: { kind: "book" } }), { "книга: 200": (x) => x.status === 200 });
  } else if (roll < 0.9) {
    check(http.get(`${BASE}/library`, { ...auth, tags: { kind: "library" } }), { "библиотека: 200": (x) => x.status === 200 });
  } else {
    check(http.get(`${BASE}/recommendations`, { ...auth, tags: { kind: "recommendations" } }), {
      "рекомендации: 200": (x) => x.status === 200,
    });
  }
}

export default function (data) {
  if (SCENARIO === "mixed") mixed(data);
  else catalog();
}

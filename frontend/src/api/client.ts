<<<<<<< HEAD
import axios from "axios";
import type { InternalAxiosRequestConfig } from "axios";
import { tokenStorage } from "./tokens";
import type { TokenPair } from "../types";

export const API_BASE = "/api/v1";

/** Основной клиент: подставляет access-токен и сам обновляет его при 401. */
export const api = axios.create({ baseURL: API_BASE });

/** Клиент без перехватчиков — для refresh и logout (чтобы не зациклиться). */
export const plainApi = axios.create({ baseURL: API_BASE });

api.interceptors.request.use((config) => {
  const token = tokenStorage.getAccess();
=======
import axios, { AxiosError } from "axios";

const TOKEN_KEY = "biblioteka_token";

export const tokenStorage = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

export const api = axios.create({ baseURL: "/api" });

api.interceptors.request.use((config) => {
  const token = tokenStorage.get();
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

<<<<<<< HEAD
const NO_REFRESH_URLS = ["/auth/login", "/auth/register", "/auth/refresh", "/auth/logout", "/auth/token"];
let refreshing: Promise<string | null> | null = null;

async function refreshTokens(): Promise<string | null> {
  const refresh = tokenStorage.getRefresh();
  if (!refresh) return null;
  try {
    const { data } = await plainApi.post<TokenPair>("/auth/refresh", { refresh_token: refresh });
    tokenStorage.set(data);
    return data.access_token;
  } catch {
    tokenStorage.clear();
    window.dispatchEvent(new Event("auth:logout"));
    return null;
  }
}

type RetriableConfig = InternalAxiosRequestConfig & { _retried?: boolean };

api.interceptors.response.use(
  (response) => response,
  async (error: unknown) => {
    if (axios.isAxiosError(error) && error.config) {
      const original = error.config as RetriableConfig;
      const skip = NO_REFRESH_URLS.some((u) => original.url?.startsWith(u));
      if (error.response?.status === 401 && !original._retried && !skip && tokenStorage.getRefresh()) {
        original._retried = true;
        // несколько запросов одновременно получили 401 — обновляем токен один раз
        refreshing = refreshing ?? refreshTokens().finally(() => (refreshing = null));
        const token = await refreshing;
        if (token) {
          original.headers.Authorization = `Bearer ${token}`;
          return api(original);
        }
      }
=======
// При 401 (кроме попыток входа) — сбрасываем токен и сообщаем приложению.
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const url = error.config?.url ?? "";
    const isAuthAttempt = url.includes("/auth/login") || url.includes("/auth/register");
    if (error.response?.status === 401 && !isAuthAttempt) {
      tokenStorage.clear();
      window.dispatchEvent(new Event("auth:logout"));
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
    }
    return Promise.reject(error);
  }
);

<<<<<<< HEAD
/** Текст ошибки для пользователя: берём detail из единого формата API. */
export function getErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string" && detail) return detail;
    if (!err.response) return "Нет связи с сервером. Проверьте подключение.";
  }
  return "Что-то пошло не так. Попробуйте ещё раз.";
=======
interface ApiErrorBody {
  error?: { code?: string; message?: string; details?: { field: string; message: string }[] };
}

/** Достаёт человекочитаемое сообщение из единого формата ошибок API. */
export function getErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const body = err.response?.data as ApiErrorBody | undefined;
    const details = body?.error?.details;
    if (details && details.length > 0) {
      return details.map((d) => `${d.field}: ${d.message}`).join("; ");
    }
    if (body?.error?.message) return body.error.message;
    if (!err.response) return "Нет связи с сервером.";
  }
  return "Произошла непредвиденная ошибка.";
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
}

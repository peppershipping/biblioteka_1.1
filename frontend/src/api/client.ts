import axios from "axios";
import type { InternalAxiosRequestConfig } from "axios";
import { tokenStorage } from "./tokens";
import type { TokenPair } from "../types";

export const API_BASE = "/api/v1";

/** Основной клиент: добавляет access-токен и обновляет его при 401. */
export const api = axios.create({ baseURL: API_BASE });

/** Клиент без перехватчиков для refresh-запросов. */
export const plainApi = axios.create({ baseURL: API_BASE });

api.interceptors.request.use((config) => {
  const token = tokenStorage.getAccess();

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

const NO_REFRESH_URLS = [
  "/auth/login",
  "/auth/register",
  "/auth/refresh",
  "/auth/logout",
  "/auth/token",
];

let refreshing: Promise<string | null> | null = null;

async function refreshTokens(): Promise<string | null> {
  const refreshToken = tokenStorage.getRefresh();

  if (!refreshToken) {
    return null;
  }

  try {
    const { data } = await plainApi.post<TokenPair>("/auth/refresh", {
      refresh_token: refreshToken,
    });

    tokenStorage.set(data);
    return data.access_token;
  } catch {
    tokenStorage.clear();
    window.dispatchEvent(new Event("auth:logout"));
    return null;
  }
}

type RetriableConfig = InternalAxiosRequestConfig & {
  _retried?: boolean;
};

api.interceptors.response.use(
  (response) => response,
  async (error: unknown) => {
    if (
      !axios.isAxiosError(error) ||
      !error.config
    ) {
      return Promise.reject(error);
    }

    const original = error.config as RetriableConfig;
    const skipRefresh = NO_REFRESH_URLS.some((url) =>
      original.url?.startsWith(url)
    );

    if (
      error.response?.status === 401 &&
      !original._retried &&
      !skipRefresh &&
      tokenStorage.getRefresh()
    ) {
      original._retried = true;

      // Одновременные запросы используют одно обновление токена.
      refreshing =
        refreshing ?? refreshTokens().finally(() => {
          refreshing = null;
        });

      const accessToken = await refreshing;

      if (accessToken) {
        original.headers.Authorization = `Bearer ${accessToken}`;
        return api(original);
      }
    }

    return Promise.reject(error);
  }
);

/** Возвращает понятное сообщение из ответа API. */
export function getErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;

    if (typeof detail === "string" && detail) {
      return detail;
    }

    if (!err.response) {
      return "Нет связи с сервером. Проверьте подключение.";
    }
  }

  return "Что-то пошло не так. Попробуйте ещё раз.";
}
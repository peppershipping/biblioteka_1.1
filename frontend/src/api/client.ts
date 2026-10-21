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
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// При 401 (кроме попыток входа) — сбрасываем токен и сообщаем приложению.
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const url = error.config?.url ?? "";
    const isAuthAttempt = url.includes("/auth/login") || url.includes("/auth/register");
    if (error.response?.status === 401 && !isAuthAttempt) {
      tokenStorage.clear();
      window.dispatchEvent(new Event("auth:logout"));
    }
    return Promise.reject(error);
  }
);

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
}

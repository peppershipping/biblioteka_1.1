import type { TokenPair } from "../types";

const ACCESS_KEY = "biblioteka.access";
const REFRESH_KEY = "biblioteka.refresh";

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

export const tokenStorage = {
  getAccess: () => read(ACCESS_KEY),
  getRefresh: () => read(REFRESH_KEY),
  set(pair: Pick<TokenPair, "access_token" | "refresh_token">) {
    try {
      localStorage.setItem(ACCESS_KEY, pair.access_token);
      localStorage.setItem(REFRESH_KEY, pair.refresh_token);
    } catch {
      /* хранилище недоступно — токены живут только до перезагрузки страницы */
    }
  },
  clear() {
    try {
      localStorage.removeItem(ACCESS_KEY);
      localStorage.removeItem(REFRESH_KEY);
    } catch {
      /* ignore */
    }
  },
};

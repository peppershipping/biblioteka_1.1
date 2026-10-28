import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { api, getErrorMessage, plainApi } from "../api/client";
import { tokenStorage } from "../api/tokens";
import type { TokenPair, User } from "../types";

interface AuthState {
  user: User | null;
  /** idle -> loading -> ready: ready значит «проверка сохранённой сессии завершена» */
  status: "idle" | "loading" | "ready";
  error: string | null;
}

const initialState: AuthState = { user: null, status: "idle", error: null };

async function loginRequest(username: string, password: string): Promise<User> {
  const { data } = await api.post<TokenPair>("/auth/login", { username, password });
  tokenStorage.set(data);
  const me = await api.get<User>("/auth/me");
  return me.data;
}

/** При старте приложения: если есть сохранённые токены — получаем профиль. */
export const initAuth = createAsyncThunk<User | null>("auth/init", async () => {
  if (!tokenStorage.getAccess() && !tokenStorage.getRefresh()) return null;
  try {
    const { data } = await api.get<User>("/auth/me");
    return data;
  } catch {
    tokenStorage.clear();
    return null;
  }
});

export const login = createAsyncThunk<User, { username: string; password: string }, { rejectValue: string }>(
  "auth/login",
  async ({ username, password }, { rejectWithValue }) => {
    try {
      return await loginRequest(username, password);
    } catch (err) {
      return rejectWithValue(getErrorMessage(err));
    }
  }
);

export const register = createAsyncThunk<
  User,
  { username: string; email: string; password: string },
  { rejectValue: string }
>("auth/register", async (payload, { rejectWithValue }) => {
  try {
    await api.post("/auth/register", payload);
    return await loginRequest(payload.username, payload.password);
  } catch (err) {
    return rejectWithValue(getErrorMessage(err));
  }
});

export const logout = createAsyncThunk<void>("auth/logout", async () => {
  const refresh = tokenStorage.getRefresh();
  tokenStorage.clear();
  if (refresh) {
    try {
      await plainApi.post("/auth/logout", { refresh_token: refresh });
    } catch {
      /* токен всё равно удалён локально */
    }
  }
});

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    /** Сессия закончилась (refresh-токен недействителен). */
    clearAuth(state) {
      state.user = null;
    },
    clearError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(initAuth.pending, (s) => {
        s.status = "loading";
      })
      .addCase(initAuth.fulfilled, (s, a) => {
        s.user = a.payload;
        s.status = "ready";
      })
      .addCase(initAuth.rejected, (s) => {
        s.status = "ready";
      })
      .addCase(login.pending, (s) => {
        s.error = null;
      })
      .addCase(login.fulfilled, (s, a) => {
        s.user = a.payload;
      })
      .addCase(login.rejected, (s, a) => {
        s.error = a.payload ?? "Не удалось войти";
      })
      .addCase(register.pending, (s) => {
        s.error = null;
      })
      .addCase(register.fulfilled, (s, a) => {
        s.user = a.payload;
      })
      .addCase(register.rejected, (s, a) => {
        s.error = a.payload ?? "Не удалось зарегистрироваться";
      })
      .addCase(logout.fulfilled, (s) => {
        s.user = null;
      });
  },
});

export const { clearAuth, clearError } = authSlice.actions;
export default authSlice.reducer;

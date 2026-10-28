import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
<<<<<<< HEAD
import { api, getErrorMessage, plainApi } from "../api/client";
import { tokenStorage } from "../api/tokens";
import type { TokenPair, User } from "../types";

interface AuthState {
  user: User | null;
  /** idle -> loading -> ready: ready значит «проверка сохранённой сессии завершена» */
=======
import { api, getErrorMessage, tokenStorage } from "../api/client";
import type { TokenResponse, User } from "../types";

interface AuthState {
  user: User | null;
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
  status: "idle" | "loading" | "ready";
  error: string | null;
}

<<<<<<< HEAD
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
=======
const initialState: AuthState = {
  user: null,
  // если токена нет — сразу "ready", проверять нечего
  status: tokenStorage.get() ? "idle" : "ready",
  error: null,
};

export const fetchMe = createAsyncThunk("auth/fetchMe", async () => {
  const { data } = await api.get<User>("/auth/me");
  return data;
});

export const login = createAsyncThunk<
  User,
  { username: string; password: string },
  { rejectValue: string }
>("auth/login", async (payload, { rejectWithValue }) => {
  try {
    const { data } = await api.post<TokenResponse>("/auth/login", payload);
    tokenStorage.set(data.access_token);
    return data.user;
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
  } catch (err) {
    return rejectWithValue(getErrorMessage(err));
  }
});

<<<<<<< HEAD
export const logout = createAsyncThunk<void>("auth/logout", async () => {
  const refresh = tokenStorage.getRefresh();
  tokenStorage.clear();
  if (refresh) {
    try {
      await plainApi.post("/auth/logout", { refresh_token: refresh });
    } catch {
      /* токен всё равно удалён локально */
    }
=======
export const register = createAsyncThunk<
  User,
  { username: string; email?: string; password: string },
  { rejectValue: string }
>("auth/register", async (payload, { rejectWithValue }) => {
  try {
    const body = { ...payload, email: payload.email || null };
    const { data } = await api.post<TokenResponse>("/auth/register", body);
    tokenStorage.set(data.access_token);
    return data.user;
  } catch (err) {
    return rejectWithValue(getErrorMessage(err));
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
  }
});

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
<<<<<<< HEAD
    /** Сессия закончилась (refresh-токен недействителен). */
    clearAuth(state) {
      state.user = null;
=======
    logout(state) {
      tokenStorage.clear();
      state.user = null;
      state.status = "ready";
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
    },
    clearError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
<<<<<<< HEAD
      .addCase(initAuth.pending, (s) => {
        s.status = "loading";
      })
      .addCase(initAuth.fulfilled, (s, a) => {
        s.user = a.payload;
        s.status = "ready";
      })
      .addCase(initAuth.rejected, (s) => {
=======
      .addCase(fetchMe.pending, (s) => {
        s.status = "loading";
      })
      .addCase(fetchMe.fulfilled, (s, a) => {
        s.user = a.payload;
        s.status = "ready";
      })
      .addCase(fetchMe.rejected, (s) => {
        tokenStorage.clear();
        s.user = null;
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
        s.status = "ready";
      })
      .addCase(login.pending, (s) => {
        s.error = null;
      })
      .addCase(login.fulfilled, (s, a) => {
        s.user = a.payload;
      })
      .addCase(login.rejected, (s, a) => {
<<<<<<< HEAD
        s.error = a.payload ?? "Не удалось войти";
=======
        s.error = a.payload ?? "Не удалось войти.";
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
      })
      .addCase(register.pending, (s) => {
        s.error = null;
      })
      .addCase(register.fulfilled, (s, a) => {
        s.user = a.payload;
      })
      .addCase(register.rejected, (s, a) => {
<<<<<<< HEAD
        s.error = a.payload ?? "Не удалось зарегистрироваться";
      })
      .addCase(logout.fulfilled, (s) => {
        s.user = null;
=======
        s.error = a.payload ?? "Не удалось зарегистрироваться.";
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
      });
  },
});

<<<<<<< HEAD
export const { clearAuth, clearError } = authSlice.actions;
=======
export const { logout, clearError } = authSlice.actions;
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
export default authSlice.reducer;

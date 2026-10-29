import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { api, getErrorMessage, plainApi } from "../api/client";
import { tokenStorage } from "../api/tokens";
import type { TokenPair, User } from "../types";

interface AuthState {
  user: User | null;
  /** ready означает, что проверка сохранённой сессии завершена. */
  status: "idle" | "loading" | "ready";
  error: string | null;
}

const initialState: AuthState = {
  user: null,
  status: "idle",
  error: null,
};

async function loginRequest(
  username: string,
  password: string,
): Promise<User> {
  const { data } = await api.post<TokenPair>("/auth/login", {
    username,
    password,
  });

  tokenStorage.set(data);

  const me = await api.get<User>("/auth/me");
  return me.data;
}

/** При запуске приложения проверяем сохранённую сессию. */
export const initAuth = createAsyncThunk<User | null>(
  "auth/init",
  async () => {
    if (!tokenStorage.getAccess() && !tokenStorage.getRefresh()) {
      return null;
    }

    try {
      const { data } = await api.get<User>("/auth/me");
      return data;
    } catch {
      tokenStorage.clear();
      return null;
    }
  },
);

export const login = createAsyncThunk<
  User,
  { username: string; password: string },
  { rejectValue: string }
>("auth/login", async ({ username, password }, { rejectWithValue }) => {
  try {
    return await loginRequest(username, password);
  } catch (err) {
    return rejectWithValue(getErrorMessage(err));
  }
});

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

export const logout = createAsyncThunk<void>(
  "auth/logout",
  async () => {
    const refreshToken = tokenStorage.getRefresh();

    // Сразу удаляем локальные токены, даже если сервер недоступен.
    tokenStorage.clear();

    if (refreshToken) {
      try {
        await plainApi.post("/auth/logout", {
          refresh_token: refreshToken,
        });
      } catch {
        // Локальная сессия уже завершена.
      }
    }
  },
);

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    /** Сессия завершена, например из-за недействительного refresh-токена. */
    clearAuth(state) {
      state.user = null;
      state.status = "ready";
      state.error = null;
    },
    clearError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(initAuth.pending, (state) => {
        state.status = "loading";
      })
      .addCase(initAuth.fulfilled, (state, action) => {
        state.user = action.payload;
        state.status = "ready";
      })
      .addCase(initAuth.rejected, (state) => {
        state.user = null;
        state.status = "ready";
      })
      .addCase(login.pending, (state) => {
        state.error = null;
      })
      .addCase(login.fulfilled, (state, action) => {
        state.user = action.payload;
        state.status = "ready";
      })
      .addCase(login.rejected, (state, action) => {
        state.error = action.payload ?? "Не удалось войти";
      })
      .addCase(register.pending, (state) => {
        state.error = null;
      })
      .addCase(register.fulfilled, (state, action) => {
        state.user = action.payload;
        state.status = "ready";
      })
      .addCase(register.rejected, (state, action) => {
        state.error = action.payload ?? "Не удалось зарегистрироваться";
      })
      .addCase(logout.fulfilled, (state) => {
        state.user = null;
        state.status = "ready";
        state.error = null;
      });
  },
});

export const { clearAuth, clearError } = authSlice.actions;
export default authSlice.reducer;
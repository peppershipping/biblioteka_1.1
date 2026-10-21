import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { api, getErrorMessage, tokenStorage } from "../api/client";
import type { TokenResponse, User } from "../types";

interface AuthState {
  user: User | null;
  status: "idle" | "loading" | "ready";
  error: string | null;
}

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
  } catch (err) {
    return rejectWithValue(getErrorMessage(err));
  }
});

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
  }
});

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    logout(state) {
      tokenStorage.clear();
      state.user = null;
      state.status = "ready";
    },
    clearError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
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
        s.status = "ready";
      })
      .addCase(login.pending, (s) => {
        s.error = null;
      })
      .addCase(login.fulfilled, (s, a) => {
        s.user = a.payload;
      })
      .addCase(login.rejected, (s, a) => {
        s.error = a.payload ?? "Не удалось войти.";
      })
      .addCase(register.pending, (s) => {
        s.error = null;
      })
      .addCase(register.fulfilled, (s, a) => {
        s.user = a.payload;
      })
      .addCase(register.rejected, (s, a) => {
        s.error = a.payload ?? "Не удалось зарегистрироваться.";
      });
  },
});

export const { logout, clearError } = authSlice.actions;
export default authSlice.reducer;

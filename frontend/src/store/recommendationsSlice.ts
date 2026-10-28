import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { api, getErrorMessage } from "../api/client";
import type { Feedback, RecommendationsPage } from "../types";

interface RecommendationsState {
  data: RecommendationsPage | null;
  loading: boolean;
  error: string | null;
}

const initialState: RecommendationsState = { data: null, loading: false, error: null };

export const fetchRecommendations = createAsyncThunk<
  RecommendationsPage,
  { limit: number; offset: number },
  { rejectValue: string }
>("recommendations/fetch", async (params, { rejectWithValue }) => {
  try {
    const { data } = await api.get<RecommendationsPage>("/recommendations", { params });
    return data;
  } catch (err) {
    return rejectWithValue(getErrorMessage(err));
  }
});

export const sendFeedback = createAsyncThunk<
  { recommendation_id: number; feedback: Feedback },
  { recommendation_id: number; feedback: Feedback },
  { rejectValue: string }
>("recommendations/feedback", async (payload, { rejectWithValue }) => {
  try {
    const { data } = await api.post<{ recommendation_id: number; feedback: Feedback }>(
      "/recommendations/feedback",
      payload
    );
    return data;
  } catch (err) {
    return rejectWithValue(getErrorMessage(err));
  }
});

const recommendationsSlice = createSlice({
  name: "recommendations",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchRecommendations.pending, (s) => {
        s.loading = true;
        s.error = null;
      })
      .addCase(fetchRecommendations.fulfilled, (s, a) => {
        s.loading = false;
        s.data = a.payload;
      })
      .addCase(fetchRecommendations.rejected, (s, a) => {
        s.loading = false;
        s.error = a.payload ?? "Не удалось загрузить рекомендации";
      })
      .addCase(sendFeedback.fulfilled, (s, a) => {
        const item = s.data?.items.find((i) => i.id === a.payload.recommendation_id);
        if (item) item.feedback = a.payload.feedback;
      })
      .addCase(sendFeedback.rejected, (s, a) => {
        s.error = a.payload ?? "Не удалось отправить отзыв";
      });
  },
});

export default recommendationsSlice.reducer;

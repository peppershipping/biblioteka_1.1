import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { api, getErrorMessage } from "../api/client";
import type { LibraryItem, Page, ReadingStatus } from "../types";

export type LibrarySort = "added" | "title" | "status" | "rating";

export interface LibraryQuery {
  status?: ReadingStatus;
  sort: LibrarySort;
  order: "asc" | "desc";
  limit: number;
  offset: number;
}

interface LibraryState {
  items: LibraryItem[];
  total: number;
  loading: boolean;
  error: string | null;
}

const initialState: LibraryState = {
  items: [],
  total: 0,
  loading: false,
  error: null,
};

export const fetchLibrary = createAsyncThunk<
  Page<LibraryItem>,
  LibraryQuery,
  { rejectValue: string }
>("library/fetch", async (query, { rejectWithValue }) => {
  try {
    const { data } = await api.get<Page<LibraryItem>>("/library", {
      params: query,
    });
    return data;
  } catch (err) {
    return rejectWithValue(getErrorMessage(err));
  }
});

const librarySlice = createSlice({
  name: "library",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchLibrary.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchLibrary.fulfilled, (state, action) => {
        state.loading = false;
        state.items = action.payload.items;
        state.total = action.payload.total;
      })
      .addCase(fetchLibrary.rejected, (state, action) => {
        state.loading = false;
        state.error =
          action.payload ?? "Не удалось загрузить библиотеку";
      });
  },
});

export default librarySlice.reducer;
import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { api, getErrorMessage } from "../api/client";
import type { LibraryEntry, ReadingStatus } from "../types";

interface LibraryState {
  entries: LibraryEntry[];
  loading: boolean;
  error: string | null;
}

const initialState: LibraryState = { entries: [], loading: false, error: null };

export const fetchLibrary = createAsyncThunk<LibraryEntry[], void, { rejectValue: string }>(
  "library/fetch",
  async (_, { rejectWithValue }) => {
    try {
      const { data } = await api.get<LibraryEntry[]>("/library");
      return data;
    } catch (err) {
      return rejectWithValue(getErrorMessage(err));
    }
  }
);

export const addToLibrary = createAsyncThunk<
  LibraryEntry,
  { bookId: number; status?: ReadingStatus },
  { rejectValue: string }
>("library/add", async ({ bookId, status }, { rejectWithValue }) => {
  try {
    const { data } = await api.post<LibraryEntry>("/library", {
      book_id: bookId,
      status: status ?? "want_to_read",
    });
    return data;
  } catch (err) {
    return rejectWithValue(getErrorMessage(err));
  }
});

export const updateStatus = createAsyncThunk<
  LibraryEntry,
  { entryId: number; status: ReadingStatus },
  { rejectValue: string }
>("library/updateStatus", async ({ entryId, status }, { rejectWithValue }) => {
  try {
    const { data } = await api.patch<LibraryEntry>(`/library/${entryId}`, { status });
    return data;
  } catch (err) {
    return rejectWithValue(getErrorMessage(err));
  }
});

export const addCustomBook = createAsyncThunk<
  LibraryEntry,
  { title: string; author: string; description: string; comment: string },
  { rejectValue: string }
>("library/addCustom", async (payload, { rejectWithValue }) => {
  try {
    const { data } = await api.post<LibraryEntry>("/library/custom", payload);
    return data;
  } catch (err) {
    return rejectWithValue(getErrorMessage(err));
  }
});

export const updateComment = createAsyncThunk<
  LibraryEntry,
  { entryId: number; comment: string },
  { rejectValue: string }
>("library/updateComment", async ({ entryId, comment }, { rejectWithValue }) => {
  try {
    const { data } = await api.patch<LibraryEntry>(`/library/${entryId}`, { comment });
    return data;
  } catch (err) {
    return rejectWithValue(getErrorMessage(err));
  }
});

export const removeFromLibrary = createAsyncThunk<number, number, { rejectValue: string }>(
  "library/remove",
  async (entryId, { rejectWithValue }) => {
    try {
      await api.delete(`/library/${entryId}`);
      return entryId;
    } catch (err) {
      return rejectWithValue(getErrorMessage(err));
    }
  }
);

const librarySlice = createSlice({
  name: "library",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchLibrary.pending, (s) => {
        s.loading = true;
        s.error = null;
      })
      .addCase(fetchLibrary.fulfilled, (s, a) => {
        s.entries = a.payload;
        s.loading = false;
      })
      .addCase(fetchLibrary.rejected, (s, a) => {
        s.loading = false;
        s.error = a.payload ?? "Не удалось загрузить библиотеку.";
      })
      .addCase(addToLibrary.fulfilled, (s, a) => {
        s.entries.unshift(a.payload);
      })
      .addCase(addCustomBook.fulfilled, (s, a) => {
        s.entries.unshift(a.payload);
      })
      .addCase(updateComment.fulfilled, (s, a) => {
        const i = s.entries.findIndex((e) => e.id === a.payload.id);
        if (i >= 0) s.entries[i] = a.payload;
      })
      .addCase(updateStatus.fulfilled, (s, a) => {
        const i = s.entries.findIndex((e) => e.id === a.payload.id);
        if (i >= 0) s.entries[i] = a.payload;
      })
      .addCase(removeFromLibrary.fulfilled, (s, a) => {
        s.entries = s.entries.filter((e) => e.id !== a.payload);
      });
  },
});

export default librarySlice.reducer;

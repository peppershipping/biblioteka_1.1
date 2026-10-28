import { configureStore } from "@reduxjs/toolkit";
import { useDispatch, useSelector } from "react-redux";
import type { TypedUseSelectorHook } from "react-redux";
import authReducer from "./authSlice";
import libraryReducer from "./librarySlice";
import recommendationsReducer from "./recommendationsSlice";

export const store = configureStore({
  reducer: {
    auth: authReducer,
    library: libraryReducer,
    recommendations: recommendationsReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

export const useAppDispatch: () => AppDispatch = useDispatch;
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;

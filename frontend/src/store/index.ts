import { configureStore } from "@reduxjs/toolkit";
import { useDispatch, useSelector } from "react-redux";
import type { TypedUseSelectorHook } from "react-redux";
import authReducer from "./authSlice";
import libraryReducer from "./librarySlice";
<<<<<<< HEAD
import recommendationsReducer from "./recommendationsSlice";
=======
>>>>>>> 088ebc434e4e609566051a7126e169906afacece

export const store = configureStore({
  reducer: {
    auth: authReducer,
    library: libraryReducer,
<<<<<<< HEAD
    recommendations: recommendationsReducer,
=======
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

export const useAppDispatch: () => AppDispatch = useDispatch;
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;

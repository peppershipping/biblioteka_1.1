import { useEffect } from "react";
import { Route, Routes } from "react-router-dom";

import AdminRoute from "./components/AdminRoute";
import Navbar from "./components/Navbar";
import PrivateRoute from "./components/PrivateRoute";
import AdminBookPage from "./pages/AdminBookPage";
import BookPage from "./pages/BookPage";
import CatalogPage from "./pages/CatalogPage";
import HomePage from "./pages/HomePage";
import LibraryPage from "./pages/LibraryPage";
import LoginPage from "./pages/LoginPage";
import NotFoundPage from "./pages/NotFoundPage";
import ProfilePage from "./pages/ProfilePage";
import RecommendationsPage from "./pages/RecommendationsPage";
import RegisterPage from "./pages/RegisterPage";
import { useAppDispatch } from "./store";
import { clearAuth, initAuth } from "./store/authSlice";

export default function App() {
  const dispatch = useAppDispatch();

  useEffect(() => {
    dispatch(initAuth());
  }, [dispatch]);

  useEffect(() => {
    const onLogout = () => {
      dispatch(clearAuth());
    };

    window.addEventListener("auth:logout", onLogout);
    return () => window.removeEventListener("auth:logout", onLogout);
  }, [dispatch]);

  useEffect(() => {
    const onLogout = () => {
      dispatch(clearAuth());
    };

    window.addEventListener("auth:logout", onLogout);
    return () => window.removeEventListener("auth:logout", onLogout);
  }, [dispatch]);

  return (
    <>
      <Navbar />
      <main className="container">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/catalog" element={<CatalogPage />} />
          <Route path="/books/:id" element={<BookPage />} />

          <Route element={<PrivateRoute />}>
            <Route path="/library" element={<LibraryPage />} />
            <Route path="/recommendations" element={<RecommendationsPage />} />
            <Route path="/profile" element={<ProfilePage />} />
          </Route>

          <Route element={<AdminRoute />}>
            <Route path="/admin/books/new" element={<AdminBookPage />} />
          </Route>

          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>
    </>
  );
}
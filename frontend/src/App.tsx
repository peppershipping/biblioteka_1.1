import { useEffect } from "react";
import { Route, Routes } from "react-router-dom";
<<<<<<< HEAD
import AdminRoute from "./components/AdminRoute";
import Navbar from "./components/Navbar";
import PrivateRoute from "./components/PrivateRoute";
import AdminBookPage from "./pages/AdminBookPage";
import BookPage from "./pages/BookPage";
import CatalogPage from "./pages/CatalogPage";
=======
import Navbar from "./components/Navbar";
import PrivateRoute from "./components/PrivateRoute";
import { tokenStorage } from "./api/client";
import { fetchMe, logout } from "./store/authSlice";
import { useAppDispatch } from "./store";
import BookPage from "./pages/BookPage";
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
import HomePage from "./pages/HomePage";
import LibraryPage from "./pages/LibraryPage";
import LoginPage from "./pages/LoginPage";
import NotFoundPage from "./pages/NotFoundPage";
import ProfilePage from "./pages/ProfilePage";
<<<<<<< HEAD
import RecommendationsPage from "./pages/RecommendationsPage";
import RegisterPage from "./pages/RegisterPage";
import { useAppDispatch } from "./store";
import { clearAuth, initAuth } from "./store/authSlice";
=======
import RegisterPage from "./pages/RegisterPage";
>>>>>>> 088ebc434e4e609566051a7126e169906afacece

export default function App() {
  const dispatch = useAppDispatch();

<<<<<<< HEAD
  useEffect(() => {
    dispatch(initAuth());
    // клиент API сообщает, что сессия закончилась (refresh-токен недействителен)
    const onLogout = () => dispatch(clearAuth());
=======
  // Восстанавливаем сессию по сохранённому токену
  useEffect(() => {
    if (tokenStorage.get()) dispatch(fetchMe());
  }, [dispatch]);

  // Интерцептор axios сообщает о протухшем токене через событие
  useEffect(() => {
    const onLogout = () => dispatch(logout());
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
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
<<<<<<< HEAD
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

=======
          <Route element={<PrivateRoute />}>
            <Route path="/books/:id" element={<BookPage />} />
            <Route path="/library" element={<LibraryPage />} />
            <Route path="/profile" element={<ProfilePage />} />
          </Route>
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>
    </>
  );
}

import { useEffect } from "react";
import { Route, Routes } from "react-router-dom";
import Navbar from "./components/Navbar";
import PrivateRoute from "./components/PrivateRoute";
import { tokenStorage } from "./api/client";
import { fetchMe, logout } from "./store/authSlice";
import { useAppDispatch } from "./store";
import BookPage from "./pages/BookPage";
import HomePage from "./pages/HomePage";
import LibraryPage from "./pages/LibraryPage";
import LoginPage from "./pages/LoginPage";
import NotFoundPage from "./pages/NotFoundPage";
import ProfilePage from "./pages/ProfilePage";
import RegisterPage from "./pages/RegisterPage";

export default function App() {
  const dispatch = useAppDispatch();

  // Восстанавливаем сессию по сохранённому токену
  useEffect(() => {
    if (tokenStorage.get()) dispatch(fetchMe());
  }, [dispatch]);

  // Интерцептор axios сообщает о протухшем токене через событие
  useEffect(() => {
    const onLogout = () => dispatch(logout());
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
          <Route element={<PrivateRoute />}>
            <Route path="/books/:id" element={<BookPage />} />
            <Route path="/library" element={<LibraryPage />} />
            <Route path="/profile" element={<ProfilePage />} />
          </Route>
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>
    </>
  );
}

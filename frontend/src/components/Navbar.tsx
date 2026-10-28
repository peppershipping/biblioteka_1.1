import { Link, NavLink, useNavigate } from "react-router-dom";
import { logout } from "../store/authSlice";
import { useAppDispatch, useAppSelector } from "../store";

export default function Navbar() {
  const user = useAppSelector((s) => s.auth.user);
  const dispatch = useAppDispatch();
  const navigate = useNavigate();

<<<<<<< HEAD
  const handleLogout = async () => {
    await dispatch(logout());
=======
  const handleLogout = () => {
    dispatch(logout());
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
    navigate("/");
  };

  return (
    <header className="navbar">
      <Link to="/" className="logo">
        Библиотека
      </Link>
      <nav className="nav-links">
<<<<<<< HEAD
        <NavLink to="/catalog">Каталог</NavLink>
        {user ? (
          <>
            <NavLink to="/library">Моя библиотека</NavLink>
            <NavLink to="/recommendations">Рекомендации</NavLink>
            {user.role === "admin" && <NavLink to="/admin/books/new">Добавить книгу</NavLink>}
=======
        {user ? (
          <>
            <NavLink to="/library">Моя библиотека</NavLink>
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
            <NavLink to="/profile">{user.username}</NavLink>
            <button className="btn btn-outline btn-sm" onClick={handleLogout}>
              Выйти
            </button>
          </>
        ) : (
          <>
            <NavLink to="/login">Вход</NavLink>
            <NavLink to="/register">Регистрация</NavLink>
          </>
        )}
      </nav>
    </header>
  );
}

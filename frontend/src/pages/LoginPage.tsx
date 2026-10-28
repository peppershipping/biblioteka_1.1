<<<<<<< HEAD
import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { clearError, login } from "../store/authSlice";
=======
import { useState } from "react";
import type { FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Link } from "react-router-dom";
import { login } from "../store/authSlice";
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
import { useAppDispatch, useAppSelector } from "../store";

export default function LoginPage() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const location = useLocation();
  const error = useAppSelector((s) => s.auth.error);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

<<<<<<< HEAD
  useEffect(() => {
    dispatch(clearError());
  }, [dispatch]);

=======
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    const result = await dispatch(login({ username, password }));
    setSubmitting(false);
    if (login.fulfilled.match(result)) {
      const from = (location.state as { from?: string } | null)?.from || "/library";
      navigate(from, { replace: true });
    }
  };

  return (
    <div className="auth-page">
      <form className="auth-form-card" onSubmit={handleSubmit}>
        <h2>Вход</h2>
        <label>
<<<<<<< HEAD
          Имя пользователя или email
=======
          Имя пользователя
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
          <input value={username} onChange={(e) => setUsername(e.target.value)} required autoFocus />
        </label>
        <label>
          Пароль
<<<<<<< HEAD
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
=======
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
        </label>
        {error && <p className="form-error">{error}</p>}
        <button className="btn btn-primary" type="submit" disabled={submitting}>
          {submitting ? "Входим…" : "Войти"}
        </button>
        <p className="muted">
          Нет аккаунта? <Link to="/register">Зарегистрироваться</Link>
        </p>
      </form>
    </div>
  );
}

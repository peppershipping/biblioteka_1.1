import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { clearError, register } from "../store/authSlice";
import { useAppDispatch, useAppSelector } from "../store";

export default function RegisterPage() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const error = useAppSelector((s) => s.auth.error);

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    dispatch(clearError());
  }, [dispatch]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    const result = await dispatch(register({ username, email, password }));
    setSubmitting(false);
    if (register.fulfilled.match(result)) navigate("/library", { replace: true });
  };

  return (
    <div className="auth-page">
      <form className="auth-form-card" onSubmit={handleSubmit}>
        <h2>Регистрация</h2>
        <label>
          Имя пользователя
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            minLength={3}
            maxLength={50}
            required
            autoFocus
          />
        </label>
        <label>
          Email
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>
          Пароль
          <input
            type="password"
            minLength={8}
            maxLength={128}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        <p className="muted small">Не менее 8 символов.</p>
        {error && <p className="form-error">{error}</p>}
        <button className="btn btn-primary" type="submit" disabled={submitting}>
          {submitting ? "Создаём аккаунт…" : "Зарегистрироваться"}
        </button>
        <p className="muted">
          Уже есть аккаунт? <Link to="/login">Войти</Link>
        </p>
      </form>
    </div>
  );
}

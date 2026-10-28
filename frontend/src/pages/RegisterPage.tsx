<<<<<<< HEAD
import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { clearError, register } from "../store/authSlice";
=======
import { useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { register } from "../store/authSlice";
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
import { useAppDispatch, useAppSelector } from "../store";

export default function RegisterPage() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const error = useAppSelector((s) => s.auth.error);

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

<<<<<<< HEAD
  useEffect(() => {
    dispatch(clearError());
  }, [dispatch]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    const result = await dispatch(register({ username, email, password }));
    setSubmitting(false);
    if (register.fulfilled.match(result)) navigate("/library", { replace: true });
=======
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    const result = await dispatch(register({ username, email: email || undefined, password }));
    setSubmitting(false);
    if (register.fulfilled.match(result)) {
      navigate("/library", { replace: true });
    }
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
  };

  return (
    <div className="auth-page">
      <form className="auth-form-card" onSubmit={handleSubmit}>
        <h2>Регистрация</h2>
        <label>
          Имя пользователя
<<<<<<< HEAD
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
=======
          <input value={username} onChange={(e) => setUsername(e.target.value)} required autoFocus />
        </label>
        <label>
          Email (необязательно)
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
        </label>
        <label>
          Пароль
          <input
            type="password"
<<<<<<< HEAD
            minLength={8}
            maxLength={128}
=======
            minLength={6}
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
<<<<<<< HEAD
        <p className="muted small">Не менее 8 символов.</p>
=======
        <p className="muted small">Не менее 6 символов.</p>
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
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

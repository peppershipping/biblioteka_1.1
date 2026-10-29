import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { clearError, login } from "../store/authSlice";
import { useAppDispatch, useAppSelector } from "../store";

export default function LoginPage() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const location = useLocation();
  const error = useAppSelector((state) => state.auth.error);

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    dispatch(clearError());
  }, [dispatch]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);

    try {
      const result = await dispatch(login({ username, password }));

      if (login.fulfilled.match(result)) {
        const from =
          (location.state as { from?: string } | null)?.from ?? "/library";

        navigate(from, { replace: true });
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-page">
      <form className="auth-form-card" onSubmit={handleSubmit}>
        <h2>Вход</h2>

        <label>
          Имя пользователя или email
          <input
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
            autoFocus
          />
        </label>

        <label>
          Пароль
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>

        {error && <p className="form-error">{error}</p>}

        <button
          className="btn btn-primary"
          type="submit"
          disabled={submitting}
        >
          {submitting ? "Входим…" : "Войти"}
        </button>

        <p className="muted">
          Нет аккаунта? <Link to="/register">Зарегистрироваться</Link>
        </p>
      </form>
    </div>
  );
}
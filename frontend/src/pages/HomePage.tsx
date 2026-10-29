import { Link } from "react-router-dom";
import { useAppSelector } from "../store";

export default function HomePage() {
  const user = useAppSelector((s) => s.auth.user);

  return (
    <section className="hero">
      <h1>Личный читательский дневник</h1>

      <p className="muted">
        Ведите свою библиотеку, отслеживайте статус чтения,
        оценивайте прочитанное по трём критериям и получайте
        персональные рекомендации.
      </p>

      <div className="hero-actions">
        <Link className="btn btn-primary" to="/catalog">
          Открыть каталог
        </Link>

        {user ? (
          <Link className="btn btn-outline" to="/library">
            Моя библиотека
          </Link>
        ) : (
          <>
            <Link className="btn btn-outline" to="/register">
              Создать аккаунт
            </Link>
            <Link className="btn btn-outline" to="/login">
              Войти
            </Link>
          </>
        )}
      </div>
    </section>
  );
}
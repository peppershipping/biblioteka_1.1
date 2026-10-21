import { Link } from "react-router-dom";
import { useAppSelector } from "../store";

export default function HomePage() {
  const user = useAppSelector((s) => s.auth.user);

  return (
    <section className="hero">
      <h1>Личный читательский дневник</h1>
      <p className="muted">
        Ведите библиотеку прочитанных и планируемых книг: добавляйте их через поиск или вручную,
        оставляйте комментарии и оценивайте по трём критериям.
      </p>
      {user ? (
        <div className="hero-actions">
          <Link className="btn btn-primary" to="/library">
            Открыть мою библиотеку
          </Link>
        </div>
      ) : (
        <div className="hero-actions">
          <Link className="btn btn-primary" to="/register">
            Начать
          </Link>
          <Link className="btn btn-outline" to="/login">
            У меня уже есть аккаунт
          </Link>
        </div>
      )}
    </section>
  );
}

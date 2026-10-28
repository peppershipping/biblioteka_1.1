import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <section className="hero">
      <h1>Страница не найдена</h1>
      <p className="muted">Такой страницы не существует.</p>
      <Link className="btn btn-primary" to="/">
        На главную
      </Link>
    </section>
  );
}

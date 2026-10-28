import { useState } from "react";
import type { FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, getErrorMessage } from "../api/client";
import type { Book } from "../types";

const EMPTY = { title: "", authors: "", genres: "", year: "", cover_url: "", description: "" };

const splitList = (value: string) =>
  value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);

/** Добавление книги в общий каталог — доступно только роли admin (ТЗ 13.1 п.9). */
export default function AdminBookPage() {
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<Book | null>(null);
  const [saving, setSaving] = useState(false);

  const set = (key: keyof typeof EMPTY) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setCreated(null);
    try {
      const { data } = await api.post<Book>("/books", {
        title: form.title,
        authors: splitList(form.authors),
        genres: splitList(form.genres),
        publication_year: form.year ? Number(form.year) : null,
        cover_url: form.cover_url || null,
        description: form.description || null,
      });
      setCreated(data);
      setForm(EMPTY);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <section>
      <h1>Добавить книгу в каталог</h1>
      <form className="panel manual-form" onSubmit={handleSubmit}>
        <label>
          Название
          <input value={form.title} onChange={set("title")} maxLength={300} required />
        </label>
        <label>
          Авторы (через запятую)
          <input value={form.authors} onChange={set("authors")} />
        </label>
        <label>
          Жанры (через запятую)
          <input value={form.genres} onChange={set("genres")} />
        </label>
        <label>
          Год публикации
          <input type="number" min={1} max={2100} value={form.year} onChange={set("year")} />
        </label>
        <label>
          Ссылка на обложку (http/https)
          <input type="url" value={form.cover_url} onChange={set("cover_url")} />
        </label>
        <label>
          Описание
          <textarea rows={5} value={form.description} onChange={set("description")} />
        </label>
        {error && <p className="form-error">{error}</p>}
        {created && (
          <p className="banner banner-info">
            Книга добавлена: <Link to={`/books/${created.id}`}>{created.title}</Link>
          </p>
        )}
        <div className="form-actions">
          <button className="btn btn-primary" type="submit" disabled={saving}>
            {saving ? "Сохраняю…" : "Добавить в каталог"}
          </button>
        </div>
      </form>
    </section>
  );
}

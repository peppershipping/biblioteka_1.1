import { useEffect, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, getErrorMessage } from "../api/client";
import {
  addCustomBook,
  addToLibrary,
  fetchLibrary,
  removeFromLibrary,
  updateStatus,
} from "../store/librarySlice";
import { useAppDispatch, useAppSelector } from "../store";
import BookCard from "../components/BookCard";
import type { Book, ReadingStatus } from "../types";
import { STATUS_LABELS } from "../types";

const FILTERS: (ReadingStatus | "")[] = ["", "want_to_read", "reading", "read"];
const EMPTY_FORM = { title: "", author: "", description: "", comment: "" };

export default function LibraryPage() {
  const dispatch = useAppDispatch();
  const { entries, loading, error } = useAppSelector((s) => s.library);
  const [filter, setFilter] = useState<ReadingStatus | "">("");

  // --- поиск по общей базе книг ("будущему каталогу") ---
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Book[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  // --- форма ручного добавления ---
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    dispatch(fetchLibrary());
  }, [dispatch]);

  useEffect(() => {
    const term = query.trim();
    if (!term) {
      setResults([]);
      setSearchError(null);
      setSearching(false);
      return;
    }
    let cancelled = false;
    setSearching(true);
    const timer = setTimeout(() => {
      api
        .get<Book[]>("/books", { params: { q: term, limit: 12 } })
        .then(({ data }) => {
          if (!cancelled) {
            setResults(data);
            setSearchError(null);
          }
        })
        .catch((err) => {
          if (!cancelled) setSearchError(getErrorMessage(err));
        })
        .finally(() => {
          if (!cancelled) setSearching(false);
        });
    }, 300);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [query]);

  const libraryBookIds = new Set(entries.map((e) => e.book_id));
  const visible = filter ? entries.filter((e) => e.status === filter) : entries;
  const nothingFound = query.trim() !== "" && !searching && !searchError && results.length === 0;

  const setField =
    (key: keyof typeof EMPTY_FORM) => (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
      setForm((f) => ({ ...f, [key]: e.target.value }));

  const openForm = () => {
    // если пользователь уже что-то искал — подставляем это как название
    setForm((f) => ({ ...f, title: f.title || query.trim() }));
    setShowForm(true);
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setFormError(null);
    const result = await dispatch(addCustomBook(form));
    setSubmitting(false);
    if (addCustomBook.fulfilled.match(result)) {
      setForm(EMPTY_FORM);
      setShowForm(false);
      setQuery("");
    } else {
      setFormError(result.payload ?? "Не удалось добавить книгу.");
    }
  };

  return (
    <section>
      <h1>Моя библиотека</h1>

      <div className="panel">
        <h2>Добавить книгу</h2>
        <input
          type="search"
          className="search-input"
          placeholder="Начните вводить название или автора…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />

        {searching && <p className="muted">Ищем…</p>}
        {searchError && <p className="form-error">{searchError}</p>}

        {results.length > 0 && (
          <div className="book-grid">
            {results.map((book) => {
              const inLibrary = libraryBookIds.has(book.id);
              return (
                <BookCard key={book.id} book={book}>
                  <button
                    className="btn btn-primary btn-sm"
                    disabled={inLibrary}
                    onClick={() => dispatch(addToLibrary({ bookId: book.id }))}
                  >
                    {inLibrary ? "Уже в библиотеке" : "Добавить в библиотеку"}
                  </button>
                </BookCard>
              );
            })}
          </div>
        )}

        {nothingFound && <p className="muted">Ничего не найдено.</p>}

        {!showForm && (
          <button className="btn btn-outline" onClick={openForm}>
            Не нашли? Добавить книгу вручную
          </button>
        )}

        {showForm && (
          <form className="manual-form" onSubmit={handleSubmit}>
            <label>
              Название
              <input value={form.title} onChange={setField("title")} maxLength={300} required />
            </label>
            <label>
              Автор
              <input value={form.author} onChange={setField("author")} maxLength={255} required />
            </label>
            <label>
              Краткое описание сюжета
              <textarea value={form.description} onChange={setField("description")} rows={3} />
            </label>
            <label>
              Комментарий
              <textarea value={form.comment} onChange={setField("comment")} rows={3} />
            </label>
            {formError && <p className="form-error">{formError}</p>}
            <div className="form-actions">
              <button className="btn btn-primary" type="submit" disabled={submitting}>
                {submitting ? "Добавляю…" : "Добавить в библиотеку"}
              </button>
              <button
                className="btn btn-ghost"
                type="button"
                onClick={() => {
                  setShowForm(false);
                  setFormError(null);
                }}
              >
                Отмена
              </button>
            </div>
          </form>
        )}
      </div>

      <div className="toolbar">
        {FILTERS.map((f) => (
          <button
            key={f || "all"}
            className={"btn btn-toggle" + (filter === f ? " active" : "")}
            onClick={() => setFilter(f)}
          >
            {f ? STATUS_LABELS[f] : "Все"}
          </button>
        ))}
      </div>

      {loading && <p className="muted">Загрузка…</p>}
      {error && <p className="form-error">{error}</p>}
      {!loading && visible.length === 0 && (
        <p className="muted">Пока пусто. Найдите книгу через поиск выше или добавьте её вручную.</p>
      )}

      <div className="book-grid">
        {visible.map((entry) => (
          <BookCard
            key={entry.id}
            book={entry.book}
            comment={entry.comment}
            rating={entry.rating}
          >
            <select
              value={entry.status}
              onChange={(e) =>
                dispatch(updateStatus({ entryId: entry.id, status: e.target.value as ReadingStatus }))
              }
            >
              {(Object.keys(STATUS_LABELS) as ReadingStatus[]).map((s) => (
                <option key={s} value={s}>
                  {STATUS_LABELS[s]}
                </option>
              ))}
            </select>
            <Link className="btn btn-outline btn-sm" to={`/books/${entry.book_id}`}>
              {entry.rating ? "Изменить оценку" : "Оценить"}
            </Link>
            <button className="btn btn-ghost btn-sm" onClick={() => dispatch(removeFromLibrary(entry.id))}>
              Удалить
            </button>
          </BookCard>
        ))}
      </div>
    </section>
  );
}

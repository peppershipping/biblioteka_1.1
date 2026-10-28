import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, getErrorMessage } from "../api/client";
import Cover from "../components/Cover";
import RatingForm from "../components/RatingForm";
import { useAppSelector } from "../store";
import type { BookDetail, Page, PublicRating, ReadingStatus } from "../types";
import { STATUSES, STATUS_LABELS } from "../types";

const RATINGS_LIMIT = 10;

export default function BookPage() {
  const { id } = useParams<{ id: string }>();
  const user = useAppSelector((s) => s.auth.user);

  const [book, setBook] = useState<BookDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [newStatus, setNewStatus] = useState<ReadingStatus>("want_to_read");
  const [ratings, setRatings] = useState<PublicRating[]>([]);
  const [ratingsTotal, setRatingsTotal] = useState(0);

  const loadBook = useCallback(async () => {
    try {
      const { data } = await api.get<BookDetail>(`/books/${id}`);
      setBook(data);
      setError(null);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  }, [id]);

  const loadRatings = useCallback(
    async (offset: number) => {
      try {
        const { data } = await api.get<Page<PublicRating>>(`/books/${id}/ratings`, {
          params: { limit: RATINGS_LIMIT, offset },
        });
        setRatings((prev) => (offset === 0 ? data.items : [...prev, ...data.items]));
        setRatingsTotal(data.total);
      } catch {
        /* список оценок необязателен для работы страницы */
      }
    },
    [id]
  );

  useEffect(() => {
    loadBook();
    loadRatings(0);
  }, [loadBook, loadRatings, user?.id]);

  if (error) return <p className="form-error">{error}</p>;
  if (!book) return <p className="muted">Загрузка…</p>;

  const reload = async () => {
    await loadBook();
    await loadRatings(0);
  };

  const changeStatus = async (status: ReadingStatus) => {
    setActionError(null);
    try {
      if (book.library_id) await api.patch(`/library/${book.library_id}`, { status });
      else await api.post("/library", { book_id: book.id, status });
      await reload();
    } catch (err) {
      setActionError(getErrorMessage(err));
    }
  };

  const removeFromLibrary = async () => {
    if (!book.library_id) return;
    setActionError(null);
    try {
      await api.delete(`/library/${book.library_id}`);
      await reload();
    } catch (err) {
      setActionError(getErrorMessage(err));
    }
  };

  return (
    <section className="book-page">
      <Link to="/catalog" className="back-link">
        ← К каталогу
      </Link>

      <div className="book-header">
        <Cover url={book.cover_url} title={book.title} large />
        <div>
          <h1>{book.title}</h1>
          <p className="author">
            {book.authors.join(", ") || "Автор не указан"}
            {book.publication_year ? ` · ${book.publication_year}` : ""}
          </p>
          {book.genres.length > 0 && (
            <div className="tags">
              {book.genres.map((g) => (
                <span key={g} className="tag">
                  {g}
                </span>
              ))}
            </div>
          )}
          <p className="avg-rating">
            {book.avg_rating != null ? (
              <>
                Средняя оценка читателей: <strong>★ {book.avg_rating.toFixed(1)}</strong>{" "}
                <span className="muted">({book.ratings_count})</span>
              </>
            ) : (
              <span className="muted">Книгу пока никто не оценил</span>
            )}
          </p>
        </div>
      </div>

      <h3>Описание</h3>
      <p className="plot-full">{book.description || "Описание не добавлено."}</p>

      {!user ? (
        <p className="banner banner-info">
          <Link to="/login">Войдите</Link>, чтобы добавить книгу в библиотеку и оценить её.
        </p>
      ) : (
        <>
          <div className="status-row">
            {book.library_id ? (
              <>
                <label>
                  Статус чтения
                  <select value={book.my_status ?? "want_to_read"} onChange={(e) => changeStatus(e.target.value as ReadingStatus)}>
                    {STATUSES.map((s) => (
                      <option key={s} value={s}>
                        {STATUS_LABELS[s]}
                      </option>
                    ))}
                  </select>
                </label>
                <button className="btn btn-ghost btn-sm" onClick={removeFromLibrary}>
                  Убрать из библиотеки
                </button>
              </>
            ) : (
              <>
                <label>
                  Добавить как
                  <select value={newStatus} onChange={(e) => setNewStatus(e.target.value as ReadingStatus)}>
                    {STATUSES.map((s) => (
                      <option key={s} value={s}>
                        {STATUS_LABELS[s]}
                      </option>
                    ))}
                  </select>
                </label>
                <button className="btn btn-primary" onClick={() => changeStatus(newStatus)}>
                  Добавить в библиотеку
                </button>
              </>
            )}
          </div>
          {actionError && <p className="form-error">{actionError}</p>}

          {book.library_id && book.my_status && (
            <RatingForm bookId={book.id} status={book.my_status} onSaved={reload} />
          )}
        </>
      )}

      <h3>Оценки читателей</h3>
      {ratings.length === 0 ? (
        <p className="muted">Оценок пока нет.</p>
      ) : (
        <div className="table-wrap">
          <table className="ratings-table">
            <thead>
              <tr>
                <th>Читатель</th>
                <th>Сюжет</th>
                <th>Персонажи</th>
                <th>Стиль</th>
                <th>Итог</th>
              </tr>
            </thead>
            <tbody>
              {ratings.map((r) => (
                <tr key={r.username}>
                  <td>{r.username}</td>
                  <td>{r.plot}</td>
                  <td>{r.characters}</td>
                  <td>{r.style}</td>
                  <td>
                    <strong>{r.total.toFixed(1)}</strong>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {ratings.length < ratingsTotal && (
        <button className="btn btn-outline btn-sm" onClick={() => loadRatings(ratings.length)}>
          Показать ещё
        </button>
      )}
    </section>
  );
}

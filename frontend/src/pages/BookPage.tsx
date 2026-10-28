<<<<<<< HEAD
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
=======
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, getErrorMessage } from "../api/client";
import {
  addToLibrary,
  fetchLibrary,
  removeFromLibrary,
  updateComment,
  updateStatus,
} from "../store/librarySlice";
import { useAppDispatch, useAppSelector } from "../store";
import RatingForm from "../components/RatingForm";
import type { BookDetail, ReadingStatus } from "../types";
import { STATUS_LABELS } from "../types";

export default function BookPage() {
  const { id } = useParams<{ id: string }>();
  const dispatch = useAppDispatch();
  const libraryEntries = useAppSelector((s) => s.library.entries);

  const [book, setBook] = useState<BookDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [commentDraft, setCommentDraft] = useState("");
  const [commentSaved, setCommentSaved] = useState(false);

  const entry = libraryEntries.find((e) => e.book_id === Number(id));

  const load = () => {
    api
      .get<BookDetail>(`/books/${id}`)
      .then(({ data }) => setBook(data))
      .catch((err) => setError(getErrorMessage(err)));
  };

  useEffect(() => {
    load();
    if (libraryEntries.length === 0) dispatch(fetchLibrary());
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // синхронизируем черновик комментария с тем, что лежит в библиотеке
  useEffect(() => {
    setCommentDraft(entry?.comment ?? "");
    setCommentSaved(false);
  }, [entry?.id, entry?.comment]);
>>>>>>> 088ebc434e4e609566051a7126e169906afacece

  if (error) return <p className="form-error">{error}</p>;
  if (!book) return <p className="muted">Загрузка…</p>;

<<<<<<< HEAD
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
=======
  const handleStatusChange = async (status: ReadingStatus) => {
    if (entry) {
      await dispatch(updateStatus({ entryId: entry.id, status }));
    } else {
      await dispatch(addToLibrary({ bookId: book.id, status }));
    }
    load();
  };

  const handleRemove = async () => {
    if (!entry) return;
    await dispatch(removeFromLibrary(entry.id));
    load();
  };

  const handleSaveComment = async () => {
    if (!entry) return;
    const result = await dispatch(updateComment({ entryId: entry.id, comment: commentDraft }));
    setCommentSaved(updateComment.fulfilled.match(result));
  };

  const handleRated = () => {
    // оценка переводит книгу в статус «Прочитано» — обновляем библиотеку
    load();
    dispatch(fetchLibrary());
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
  };

  return (
    <section className="book-page">
<<<<<<< HEAD
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
=======
      <Link to="/library" className="back-link">
        ← К моей библиотеке
      </Link>
      <h1>{book.title}</h1>
      <p className="author">
        {book.authors.map((a) => a.name).join(", ") || "Автор не указан"}
        {book.publication_year ? ` · ${book.publication_year}` : ""}
      </p>

      <h3>Краткое описание сюжета</h3>
      <p className="plot-full">{book.description || "Описание не добавлено."}</p>

      <div className="status-row">
        <label>
          Статус чтения
          <select
            value={entry?.status ?? ""}
            onChange={(e) => handleStatusChange(e.target.value as ReadingStatus)}
          >
            <option value="" disabled>
              Не в библиотеке
            </option>
            {(Object.keys(STATUS_LABELS) as ReadingStatus[]).map((s) => (
              <option key={s} value={s}>
                {STATUS_LABELS[s]}
              </option>
            ))}
          </select>
        </label>
        {entry && (
          <button className="btn btn-ghost btn-sm" onClick={handleRemove}>
            Убрать из библиотеки
          </button>
        )}
      </div>

      {entry ? (
        <>
          <div className="panel comment-panel">
            <h3>Мой комментарий</h3>
            <textarea
              rows={4}
              value={commentDraft}
              onChange={(e) => {
                setCommentDraft(e.target.value);
                setCommentSaved(false);
              }}
              placeholder="Впечатления, цитаты, мысли о книге…"
            />
            <div className="form-actions">
              <button
                className="btn btn-primary btn-sm"
                onClick={handleSaveComment}
                disabled={commentDraft === (entry.comment ?? "")}
              >
                Сохранить комментарий
              </button>
              {commentSaved && <span className="muted">Сохранено</span>}
            </div>
          </div>

          <RatingForm entryId={entry.id} onSaved={handleRated} />
        </>
      ) : (
        <p className="muted">Добавьте книгу в библиотеку, чтобы оставить комментарий и оценку.</p>
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
      )}
    </section>
  );
}

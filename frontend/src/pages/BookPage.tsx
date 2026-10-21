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

  if (error) return <p className="form-error">{error}</p>;
  if (!book) return <p className="muted">Загрузка…</p>;

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
  };

  return (
    <section className="book-page">
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
      )}
    </section>
  );
}

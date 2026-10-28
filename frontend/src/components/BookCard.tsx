import type { ReactNode } from "react";
import { Link } from "react-router-dom";
<<<<<<< HEAD
import type { Book, ReadingStatus } from "../types";
import { STATUS_LABELS } from "../types";
import Cover from "./Cover";

interface Props {
  book: Book;
  status?: ReadingStatus | null; // статус чтения текущего пользователя
  rating?: number | null; // итоговая оценка текущего пользователя
  extra?: ReactNode; // доп. информация между описанием и действиями (например, причина рекомендации)
  children?: ReactNode; // блок действий
}

/** Карточка книги: обложка, название, автор, жанр, статус чтения и оценка пользователя (ТЗ раздел 10). */
export default function BookCard({ book, status, rating, extra, children }: Props) {
  return (
    <article className="book-card">
      <Cover url={book.cover_url} title={book.title} />
      <div className="book-card-body">
        <h3>
          <Link to={`/books/${book.id}`}>{book.title}</Link>
        </h3>
        <p className="author">{book.authors.join(", ") || "Автор не указан"}</p>
        {book.genres.length > 0 && (
          <div className="tags">
            {book.genres.slice(0, 3).map((g) => (
              <span key={g} className="tag">
                {g}
              </span>
            ))}
          </div>
        )}
        {(status || rating != null) && (
          <div className="card-marks">
            {status && <span className={`badge badge-${status}`}>{STATUS_LABELS[status]}</span>}
            {rating != null && <span className="badge badge-rating">★ {rating.toFixed(1)}</span>}
          </div>
        )}
        {extra}
        {children && <div className="book-actions">{children}</div>}
      </div>
=======
import type { Book, Rating } from "../types";

interface Props {
  book: Book;
  comment?: string; // личный комментарий пользователя
  rating?: Rating | null; // оценка пользователя: сюжет, персонажи, стиль, общая
  children?: ReactNode; // блок действий под карточкой
}

export default function BookCard({ book, comment, rating, children }: Props) {
  return (
    <article className="book-card">
      <h3>
        <Link to={`/books/${book.id}`}>{book.title}</Link>
      </h3>
      <p className="author">{book.authors.map((a) => a.name).join(", ") || "Автор не указан"}</p>
      {book.description && <p className="plot">{book.description}</p>}
      {rating && (
        <ul className="rating-chips">
          <li>
            Сюжет <strong>{rating.plot}</strong>
          </li>
          <li>
            Персонажи <strong>{rating.characters}</strong>
          </li>
          <li>
            Стиль <strong>{rating.style}</strong>
          </li>
          <li className="overall">
            Общая <strong>{rating.total.toFixed(1)}</strong>
          </li>
        </ul>
      )}
      {comment && (
        <p className="comment">
          <strong>Мой комментарий:</strong> {comment}
        </p>
      )}
      {children && <div className="book-actions">{children}</div>}
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
    </article>
  );
}

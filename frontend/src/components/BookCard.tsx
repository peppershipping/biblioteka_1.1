import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import type { Book, ReadingStatus } from "../types";
import { STATUS_LABELS } from "../types";
import Cover from "./Cover";

interface Props {
  book: Book;
  status?: ReadingStatus | null;
  rating?: number | null;
  extra?: ReactNode;
  children?: ReactNode;
}

/** Карточка книги в каталоге, библиотеке и рекомендациях. */
export default function BookCard({
  book,
  status,
  rating,
  extra,
  children,
}: Props) {
  return (
    <article className="book-card">
      <Cover url={book.cover_url} title={book.title} />

      <div className="book-card-body">
        <h3>
          <Link to={`/books/${book.id}`}>{book.title}</Link>
        </h3>

        <p className="author">
          {book.authors.join(", ") || "Автор не указан"}
        </p>

        {book.genres.length > 0 && (
          <div className="tags">
            {book.genres.slice(0, 3).map((genre) => (
              <span key={genre} className="tag">
                {genre}
              </span>
            ))}
          </div>
        )}

        {(status || rating != null) && (
          <div className="card-marks">
            {status && (
              <span className={`badge badge-${status}`}>
                {STATUS_LABELS[status]}
              </span>
            )}

            {rating != null && (
              <span className="badge badge-rating">
                ★ {rating.toFixed(1)}
              </span>
            )}
          </div>
        )}

        {extra}

        {children && <div className="book-actions">{children}</div>}
      </div>
    </article>
  );
}
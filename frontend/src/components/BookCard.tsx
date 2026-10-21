import type { ReactNode } from "react";
import { Link } from "react-router-dom";
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
    </article>
  );
}

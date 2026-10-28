import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, getErrorMessage } from "../api/client";
import BookCard from "../components/BookCard";
import Pagination from "../components/Pagination";
import { useAppSelector } from "../store";
import type { BookListItem, BookPage, Genre } from "../types";

const LIMIT = 12;
type Sort = "relevance" | "title" | "year" | "created";

const SORT_LABELS: Record<Sort, string> = {
  relevance: "По релевантности",
  title: "По названию",
  year: "По году",
  created: "По новизне",
};

export default function CatalogPage() {
  const user = useAppSelector((s) => s.auth.user);

  const [q, setQ] = useState("");
  const [author, setAuthor] = useState("");
  const [year, setYear] = useState("");
  const [genre, setGenre] = useState("");
  const [sort, setSort] = useState<Sort>("relevance");
  const [order, setOrder] = useState<"asc" | "desc">("asc");
  const [smart, setSmart] = useState(false);
  const [offset, setOffset] = useState(0);

  const [genres, setGenres] = useState<Genre[]>([]);
  const [page, setPage] = useState<BookPage | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // любое изменение фильтра возвращает на первую страницу
  const filter =
    <T,>(setter: (value: T) => void) =>
    (value: T) => {
      setter(value);
      setOffset(0);
    };

  useEffect(() => {
    api
      .get<Genre[]>("/genres")
      .then(({ data }) => setGenres(data))
      .catch(() => setGenres([]));
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const timer = setTimeout(() => {
      const params: Record<string, string | number | boolean> = { limit: LIMIT, offset, sort, order };
      if (q.trim()) params.q = q.trim();
      if (author.trim()) params.author = author.trim();
      if (genre) params.genre = genre;
      const yearNumber = Number(year);
      if (year && Number.isInteger(yearNumber) && yearNumber >= 1 && yearNumber <= 2100) params.year = yearNumber;
      if (smart && q.trim()) params.smart = true;

      api
        .get<BookPage>("/books/search", { params })
        .then(({ data }) => {
          if (!cancelled) {
            setPage(data);
            setError(null);
          }
        })
        .catch((err) => {
          if (!cancelled) setError(getErrorMessage(err));
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }, 300);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [q, author, year, genre, sort, order, smart, offset, user?.id]);

  const addToLibrary = async (book: BookListItem) => {
    setNotice(null);
    try {
      await api.post("/library", { book_id: book.id });
      setPage((p) =>
        p ? { ...p, items: p.items.map((i) => (i.id === book.id ? { ...i, my_status: "want_to_read" } : i)) } : p
      );
    } catch (err) {
      setNotice(getErrorMessage(err));
    }
  };

  const interpreted = page?.interpreted;

  return (
    <section>
      <h1>Каталог</h1>

      <div className="panel filters">
        <input
          type="search"
          className="search-input"
          placeholder="Поиск по названию, автору, описанию, жанру…"
          value={q}
          onChange={(e) => filter(setQ)(e.target.value)}
        />
        <div className="filter-row">
          <select value={genre} onChange={(e) => filter(setGenre)(e.target.value)} aria-label="Жанр">
            <option value="">Все жанры</option>
            {genres.map((g) => (
              <option key={g.id} value={g.name}>
                {g.name}
              </option>
            ))}
          </select>
          <input
            placeholder="Автор"
            value={author}
            onChange={(e) => filter(setAuthor)(e.target.value)}
            aria-label="Автор"
          />
          <input
            type="number"
            min={1}
            max={2100}
            placeholder="Год"
            value={year}
            onChange={(e) => filter(setYear)(e.target.value)}
            aria-label="Год публикации"
          />
          <select value={sort} onChange={(e) => filter(setSort)(e.target.value as Sort)} aria-label="Сортировка">
            {(Object.keys(SORT_LABELS) as Sort[]).map((s) => (
              <option key={s} value={s}>
                {SORT_LABELS[s]}
              </option>
            ))}
          </select>
          <select value={order} onChange={(e) => filter(setOrder)(e.target.value as "asc" | "desc")} aria-label="Порядок">
            <option value="asc">по возрастанию</option>
            <option value="desc">по убыванию</option>
          </select>
        </div>
        <label className="checkbox-inline">
          <input type="checkbox" checked={smart} onChange={(e) => filter(setSmart)(e.target.checked)} />
          Умный поиск: ИИ разберёт запрос на естественном языке (например, «фантастика про космос 1960-х»)
        </label>
      </div>

      {interpreted && (
        <p className="banner banner-info">
          ИИ понял запрос так:
          {interpreted.q && <> ключевые слова «{interpreted.q}»</>}
          {interpreted.genre && <>, жанр «{interpreted.genre}»</>}
          {interpreted.year && <>, год {interpreted.year}</>}.
        </p>
      )}
      {notice && <p className="form-error">{notice}</p>}
      {error && <p className="form-error">{error}</p>}
      {loading && !page && <p className="muted">Загрузка…</p>}
      {page && page.items.length === 0 && !loading && <p className="muted">Ничего не найдено. Измените запрос или фильтры.</p>}

      <div className="book-grid">
        {page?.items.map((book) => (
          <BookCard key={book.id} book={book} status={book.my_status} rating={book.my_rating}>
            {user ? (
              !book.my_status && (
                <button className="btn btn-primary btn-sm" onClick={() => addToLibrary(book)}>
                  Добавить в библиотеку
                </button>
              )
            ) : (
              <Link className="btn btn-outline btn-sm" to="/login">
                Войдите, чтобы добавить
              </Link>
            )}
          </BookCard>
        ))}
      </div>

      {page && <Pagination total={page.total} limit={LIMIT} offset={offset} onChange={setOffset} />}
    </section>
  );
}

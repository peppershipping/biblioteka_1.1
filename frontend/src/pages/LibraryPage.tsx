import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, getErrorMessage } from "../api/client";
import BookCard from "../components/BookCard";
import Pagination from "../components/Pagination";
import { fetchLibrary } from "../store/librarySlice";
import type { LibrarySort } from "../store/librarySlice";
import { useAppDispatch, useAppSelector } from "../store";
import type { ReadingStatus } from "../types";
import { STATUSES, STATUS_LABELS } from "../types";

const LIMIT = 12;

const SORT_LABELS: Record<LibrarySort, string> = {
  added: "По дате добавления",
  title: "По названию",
  status: "По статусу",
  rating: "По оценке",
};

export default function LibraryPage() {
  const dispatch = useAppDispatch();
  const { items, total, loading, error } = useAppSelector((s) => s.library);

  const [status, setStatus] = useState<ReadingStatus | "">("");
  const [sort, setSort] = useState<LibrarySort>("added");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [offset, setOffset] = useState(0);
  const [actionError, setActionError] = useState<string | null>(null);

  const load = useCallback(() => {
    dispatch(fetchLibrary({ status: status || undefined, sort, order, limit: LIMIT, offset }));
  }, [dispatch, status, sort, order, offset]);

  useEffect(() => {
    load();
  }, [load]);

  const changeStatus = async (entryId: number, next: ReadingStatus) => {
    setActionError(null);
    try {
      await api.patch(`/library/${entryId}`, { status: next });
      load();
    } catch (err) {
      setActionError(getErrorMessage(err));
    }
  };

  const remove = async (entryId: number) => {
    setActionError(null);
    try {
      await api.delete(`/library/${entryId}`);
      // удалили последнюю запись на странице — возвращаемся на предыдущую
      if (items.length === 1 && offset > 0) setOffset(offset - LIMIT);
      else load();
    } catch (err) {
      setActionError(getErrorMessage(err));
    }
  };

  const applyFilter = (next: ReadingStatus | "") => {
    setStatus(next);
    setOffset(0);
  };

  return (
    <section>
      <h1>Моя библиотека</h1>

      <div className="toolbar">
        <button className={"btn btn-toggle" + (status === "" ? " active" : "")} onClick={() => applyFilter("")}>
          Все
        </button>
        {STATUSES.map((s) => (
          <button
            key={s}
            className={"btn btn-toggle" + (status === s ? " active" : "")}
            onClick={() => applyFilter(s)}
          >
            {STATUS_LABELS[s]}
          </button>
        ))}
        <select
          value={sort}
          onChange={(e) => {
            setSort(e.target.value as LibrarySort);
            setOffset(0);
          }}
          aria-label="Сортировка"
        >
          {(Object.keys(SORT_LABELS) as LibrarySort[]).map((s) => (
            <option key={s} value={s}>
              {SORT_LABELS[s]}
            </option>
          ))}
        </select>
        <select
          value={order}
          onChange={(e) => {
            setOrder(e.target.value as "asc" | "desc");
            setOffset(0);
          }}
          aria-label="Порядок"
        >
          <option value="desc">по убыванию</option>
          <option value="asc">по возрастанию</option>
        </select>
      </div>

      {loading && items.length === 0 && <p className="muted">Загрузка…</p>}
      {error && <p className="form-error">{error}</p>}
      {actionError && <p className="form-error">{actionError}</p>}
      {!loading && items.length === 0 && (
        <p className="muted">
          Здесь пока пусто. <Link to="/catalog">Найдите книги в каталоге</Link>.
        </p>
      )}

      <div className="book-grid">
        {items.map((entry) => (
          <BookCard key={entry.id} book={entry.book} rating={entry.rating?.total ?? null}>
            <select
              value={entry.status}
              onChange={(e) => changeStatus(entry.id, e.target.value as ReadingStatus)}
              aria-label="Статус чтения"
            >
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {STATUS_LABELS[s]}
                </option>
              ))}
            </select>
            <Link className="btn btn-outline btn-sm" to={`/books/${entry.book_id}`}>
              {entry.rating ? "Изменить оценку" : entry.status === "read" ? "Оценить" : "Подробнее"}
            </Link>
            <button className="btn btn-ghost btn-sm" onClick={() => remove(entry.id)}>
              Удалить
            </button>
          </BookCard>
        ))}
      </div>

      <Pagination total={total} limit={LIMIT} offset={offset} onChange={setOffset} />
    </section>
  );
}

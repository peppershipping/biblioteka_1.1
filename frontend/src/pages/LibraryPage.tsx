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
  const { items, total, loading, error } = useAppSelector(
    (state) => state.library
  );

  const [status, setStatus] = useState<ReadingStatus | "">("");
  const [sort, setSort] = useState<LibrarySort>("added");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [offset, setOffset] = useState(0);
  const [actionError, setActionError] = useState<string | null>(null);

  const load = useCallback(() => {
    dispatch(
      fetchLibrary({
        status: status || undefined,
        sort,
        order,
        limit: LIMIT,
        offset,
      })
    );
  }, [dispatch, status, sort, order, offset]);

  useEffect(() => {
    load();
  }, [load]);

  const changeStatus = async (
    entryId: number,
    nextStatus: ReadingStatus
  ) => {
    setActionError(null);

    try {
      await api.patch(`/library/${entryId}`, { status: nextStatus });
      load();
    } catch (err) {
      setActionError(getErrorMessage(err));
    }
  };

  const remove = async (entryId: number) => {
    setActionError(null);

    try {
      await api.delete(`/library/${entryId}`);

      if (items.length === 1 && offset > 0) {
        setOffset((current) => Math.max(0, current - LIMIT));
      } else {
        load();
      }
    } catch (err) {
      setActionError(getErrorMessage(err));
    }
  };

  const applyFilter = (nextStatus: ReadingStatus | "") => {
    setStatus(nextStatus);
    setOffset(0);
  };

  return (
    <section>
      <h1>Моя библиотека</h1>

      <div className="toolbar">
        <button
          className={`btn btn-toggle${status === "" ? " active" : ""}`}
          onClick={() => applyFilter("")}
        >
          Все
        </button>

        {STATUSES.map((itemStatus) => (
          <button
            key={itemStatus}
            className={`btn btn-toggle${
              status === itemStatus ? " active" : ""
            }`}
            onClick={() => applyFilter(itemStatus)}
          >
            {STATUS_LABELS[itemStatus]}
          </button>
        ))}

        <select
          value={sort}
          onChange={(event) => {
            setSort(event.target.value as LibrarySort);
            setOffset(0);
          }}
          aria-label="Сортировка"
        >
          {(Object.keys(SORT_LABELS) as LibrarySort[]).map((itemSort) => (
            <option key={itemSort} value={itemSort}>
              {SORT_LABELS[itemSort]}
            </option>
          ))}
        </select>

        <select
          value={order}
          onChange={(event) => {
            setOrder(event.target.value as "asc" | "desc");
            setOffset(0);
          }}
          aria-label="Порядок сортировки"
        >
          <option value="desc">По убыванию</option>
          <option value="asc">По возрастанию</option>
        </select>
      </div>

      {loading && items.length === 0 && (
        <p className="muted">Загрузка…</p>
      )}

      {error && <p className="form-error">{error}</p>}
      {actionError && <p className="form-error">{actionError}</p>}

      {!loading && items.length === 0 && (
        <p className="muted">
          Здесь пока пусто.{" "}
          <Link to="/catalog">Найдите книги в каталоге</Link>.
        </p>
      )}

      <div className="book-grid">
        {items.map((entry) => (
          <BookCard
            key={entry.id}
            book={entry.book}
            status={entry.status}
            rating={entry.rating?.total ?? null}
          >
            <select
              value={entry.status}
              onChange={(event) =>
                void changeStatus(
                  entry.id,
                  event.target.value as ReadingStatus
                )
              }
              aria-label="Статус чтения"
            >
              {STATUSES.map((itemStatus) => (
                <option key={itemStatus} value={itemStatus}>
                  {STATUS_LABELS[itemStatus]}
                </option>
              ))}
            </select>

            <Link
              className="btn btn-outline btn-sm"
              to={`/books/${entry.book_id}`}
            >
              {entry.rating
                ? "Изменить оценку"
                : entry.status === "read"
                  ? "Оценить"
                  : "Подробнее"}
            </Link>

            <button
              className="btn btn-ghost btn-sm"
              onClick={() => void remove(entry.id)}
            >
              Удалить
            </button>
          </BookCard>
        ))}
      </div>

      <Pagination
        total={total}
        limit={LIMIT}
        offset={offset}
        onChange={setOffset}
      />
    </section>
  );
}
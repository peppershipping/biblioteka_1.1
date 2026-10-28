import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, getErrorMessage } from "../api/client";
import BookCard from "../components/BookCard";
import Pagination from "../components/Pagination";
import { fetchRecommendations, sendFeedback } from "../store/recommendationsSlice";
import { useAppDispatch, useAppSelector } from "../store";

const LIMIT = 12;

export default function RecommendationsPage() {
  const dispatch = useAppDispatch();
  const { data, loading, error } = useAppSelector((s) => s.recommendations);
  const [offset, setOffset] = useState(0);
  const [added, setAdded] = useState<Set<number>>(new Set());
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    dispatch(fetchRecommendations({ limit: LIMIT, offset }));
  }, [dispatch, offset]);

  const addToLibrary = async (bookId: number) => {
    setNotice(null);
    try {
      await api.post("/library", { book_id: bookId });
      setAdded((prev) => new Set(prev).add(bookId));
    } catch (err) {
      setNotice(getErrorMessage(err));
    }
  };

  return (
    <section>
      <h1>Рекомендации</h1>

      {loading && !data && <p className="muted">Подбираем книги…</p>}
      {error && <p className="form-error">{error}</p>}
      {notice && <p className="form-error">{notice}</p>}

      {data && (
        <>
          {data.message && (
            <p className="banner banner-info">
              {data.message} <Link to="/library">Перейти в библиотеку</Link>
            </p>
          )}
          <h2>{data.personalized ? "Подобрано для вас" : "Популярные книги"}</h2>
          {data.personalized && !data.explanations && (
            <p className="muted small">Пояснения ИИ сейчас недоступны — показан только алгоритмический подбор.</p>
          )}
          {data.items.length === 0 && <p className="muted">Пока нечего предложить — каталог пуст.</p>}

          <div className="book-grid">
            {data.items.map((rec) => (
              <BookCard
                key={rec.id}
                book={rec.book}
                extra={
                  <>
                    {rec.reason && <p className="reco-reason">{rec.reason}</p>}
                    {rec.signals.similar_to && (
                      <p className="small muted">Похоже на «{rec.signals.similar_to}»</p>
                    )}
                    {rec.signals.genres.length > 0 && (
                      <p className="small muted">Общие жанры: {rec.signals.genres.join(", ")}</p>
                    )}
                  </>
                }
              >
                <button
                  className="btn btn-primary btn-sm"
                  disabled={added.has(rec.book.id)}
                  onClick={() => addToLibrary(rec.book.id)}
                >
                  {added.has(rec.book.id) ? "В библиотеке" : "Добавить в библиотеку"}
                </button>
                <div className="feedback" role="group" aria-label="Оценка рекомендации">
                  <button
                    className={"btn btn-toggle btn-sm" + (rec.feedback === "helpful" ? " active" : "")}
                    onClick={() => dispatch(sendFeedback({ recommendation_id: rec.id, feedback: "helpful" }))}
                  >
                    Полезно
                  </button>
                  <button
                    className={"btn btn-toggle btn-sm" + (rec.feedback === "not_helpful" ? " active" : "")}
                    onClick={() => dispatch(sendFeedback({ recommendation_id: rec.id, feedback: "not_helpful" }))}
                  >
                    Не полезно
                  </button>
                </div>
              </BookCard>
            ))}
          </div>

          <Pagination total={data.total} limit={LIMIT} offset={offset} onChange={setOffset} />
        </>
      )}
    </section>
  );
}

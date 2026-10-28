<<<<<<< HEAD
import { useEffect, useState } from "react";
import { api, getErrorMessage } from "../api/client";
import { useAppSelector } from "../store";
import type { LibraryStats } from "../types";

export default function ProfilePage() {
  const user = useAppSelector((s) => s.auth.user);
  const [stats, setStats] = useState<LibraryStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<LibraryStats>("/library/stats")
      .then(({ data }) => setStats(data))
      .catch((err) => setError(getErrorMessage(err)));
  }, []);
=======
import { useEffect } from "react";
import { fetchLibrary } from "../store/librarySlice";
import { useAppDispatch, useAppSelector } from "../store";

export default function ProfilePage() {
  const dispatch = useAppDispatch();
  const user = useAppSelector((s) => s.auth.user);
  const entries = useAppSelector((s) => s.library.entries);

  useEffect(() => {
    dispatch(fetchLibrary());
  }, [dispatch]);

  const total = entries.length;
  const read = entries.filter((e) => e.status === "read").length;
  const reading = entries.filter((e) => e.status === "reading").length;
  const wantToRead = entries.filter((e) => e.status === "want_to_read").length;
  const rated = entries.filter((e) => e.my_rating != null);
  const avgRating = rated.length
    ? rated.reduce((sum, e) => sum + (e.my_rating ?? 0), 0) / rated.length
    : null;
>>>>>>> 088ebc434e4e609566051a7126e169906afacece

  if (!user) return null;

  return (
    <section>
      <h1>Профиль</h1>
      <div className="profile-card">
        <p>
          <strong>Имя пользователя:</strong> {user.username}
        </p>
<<<<<<< HEAD
        <p>
          <strong>Email:</strong> {user.email}
        </p>
        <p>
          <strong>Роль:</strong> {user.role === "admin" ? "администратор" : "пользователь"}
        </p>
      </div>

      <h2>Статистика библиотеки</h2>
      {error && <p className="form-error">{error}</p>}
      {stats && (
        <div className="stats-grid">
          <div className="stat-box">
            <span className="stat-value">{stats.total}</span>
            <span className="stat-label">Всего книг</span>
          </div>
          <div className="stat-box">
            <span className="stat-value">{stats.want_to_read}</span>
            <span className="stat-label">Хочу прочитать</span>
          </div>
          <div className="stat-box">
            <span className="stat-value">{stats.in_progress}</span>
            <span className="stat-label">В процессе</span>
          </div>
          <div className="stat-box">
            <span className="stat-value">{stats.read}</span>
            <span className="stat-label">Прочитано</span>
          </div>
          <div className="stat-box">
            <span className="stat-value">{stats.ratings_count}</span>
            <span className="stat-label">Оценок</span>
          </div>
          <div className="stat-box">
            <span className="stat-value">{stats.avg_rating != null ? stats.avg_rating.toFixed(1) : "—"}</span>
            <span className="stat-label">Средняя оценка</span>
          </div>
        </div>
      )}
=======
        {user.email && (
          <p>
            <strong>Email:</strong> {user.email}
          </p>
        )}
      </div>

      <h2>Статистика чтения</h2>
      <div className="stats-grid">
        <div className="stat-box">
          <span className="stat-value">{total}</span>
          <span className="stat-label">Всего книг</span>
        </div>
        <div className="stat-box">
          <span className="stat-value">{read}</span>
          <span className="stat-label">Прочитано</span>
        </div>
        <div className="stat-box">
          <span className="stat-value">{reading}</span>
          <span className="stat-label">Читаю сейчас</span>
        </div>
        <div className="stat-box">
          <span className="stat-value">{wantToRead}</span>
          <span className="stat-label">В планах</span>
        </div>
        <div className="stat-box">
          <span className="stat-value">{avgRating != null ? avgRating.toFixed(1) : "—"}</span>
          <span className="stat-label">Средняя оценка</span>
        </div>
      </div>
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
    </section>
  );
}

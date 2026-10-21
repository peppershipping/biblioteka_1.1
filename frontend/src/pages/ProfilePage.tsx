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

  if (!user) return null;

  return (
    <section>
      <h1>Профиль</h1>
      <div className="profile-card">
        <p>
          <strong>Имя пользователя:</strong> {user.username}
        </p>
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
    </section>
  );
}

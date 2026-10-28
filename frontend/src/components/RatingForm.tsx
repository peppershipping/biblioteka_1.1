import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { api, getErrorMessage } from "../api/client";
<<<<<<< HEAD
import type { Rating, ReadingStatus } from "../types";

interface Props {
  bookId: number;
  status: ReadingStatus;
  onSaved?: () => void;
=======
import type { Rating } from "../types";

interface Props {
  entryId: number;
  onSaved?: (rating: Rating) => void;
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
}

const CRITERIA = [
  { key: "plot", label: "Сюжет" },
  { key: "characters", label: "Персонажи" },
<<<<<<< HEAD
  { key: "style", label: "Язык и стиль" },
=======
  { key: "style", label: "Стиль" },
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
] as const;

type Values = Record<(typeof CRITERIA)[number]["key"], number>;

<<<<<<< HEAD
/**
 * Оценка по трём критериям (1–10). Итоговая оценка = среднее трёх — считается и
 * на сервере; здесь показывается сразу при движении ползунков. Оценивать можно
 * только прочитанные книги (правило 28) — иначе форма заблокирована.
 */
export default function RatingForm({ bookId, status, onSaved }: Props) {
  const [values, setValues] = useState<Values>({ plot: 7, characters: 7, style: 7 });
  const [saved, setSaved] = useState(false);
=======
export default function RatingForm({ entryId, onSaved }: Props) {
  const [values, setValues] = useState<Values>({ plot: 7, characters: 7, style: 7 });
  const [saved, setSaved] = useState(false); // есть ли уже сохранённая оценка
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

<<<<<<< HEAD
  const locked = status !== "read";
  const average = (values.plot + values.characters + values.style) / 3;

  useEffect(() => {
    api
      .get<Rating>(`/books/${bookId}/rating`)
=======
  // Общая оценка — среднее трёх критериев, пересчитывается прямо при движении ползунков
  // (на сервере считается так же: (сюжет + персонажи + стиль) / 3).
  const average = (values.plot + values.characters + values.style) / 3;

  // Подгружаем уже выставленную оценку (404 — значит оценки ещё нет)
  useEffect(() => {
    api
      .get<Rating>(`/library/${entryId}/rating`)
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
      .then(({ data }) => {
        setValues({ plot: data.plot, characters: data.characters, style: data.style });
        setSaved(true);
      })
      .catch(() => setSaved(false));
<<<<<<< HEAD
  }, [bookId]);
=======
  }, [entryId]);
>>>>>>> 088ebc434e4e609566051a7126e169906afacece

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
<<<<<<< HEAD
      await api.post(`/books/${bookId}/rating`, values);
      setSaved(true);
      setMessage("Оценка сохранена");
      onSaved?.();
=======
      const { data } = await api.put<Rating>(`/library/${entryId}/rating`, values);
      setSaved(true);
      setMessage("Оценка сохранена");
      onSaved?.(data);
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="rating-form" onSubmit={handleSubmit}>
      <h3>Моя оценка</h3>
<<<<<<< HEAD
      {locked && (
        <p className="banner banner-info">
          Оценка доступна, когда у книги статус «Прочитано».
          {saved && " Ранее выставленная оценка показана ниже."}
        </p>
      )}
=======
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
      {CRITERIA.map(({ key, label }) => (
        <label key={key} className="rating-row">
          <span>{label}</span>
          <input
            type="range"
            min={1}
            max={10}
<<<<<<< HEAD
            disabled={locked}
=======
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
            value={values[key]}
            onChange={(e) => {
              setValues((v) => ({ ...v, [key]: Number(e.target.value) }));
              setMessage(null);
            }}
          />
          <strong>{values[key]}</strong>
        </label>
      ))}
      <p className="overall-score">
<<<<<<< HEAD
        Итоговая оценка: <strong>{average.toFixed(1)}</strong> / 10
      </p>
      <p className="muted small">Среднее из оценок сюжета, персонажей и языка и стиля.</p>
      {error && <p className="form-error">{error}</p>}
      {!locked && (
        <div className="form-actions">
          <button className="btn btn-primary" type="submit" disabled={saving}>
            {saving ? "Сохраняю…" : saved ? "Обновить оценку" : "Сохранить оценку"}
          </button>
          {message && <span className="muted">{message}</span>}
        </div>
      )}
=======
        Общая оценка: <strong>{average.toFixed(1)}</strong> / 10
      </p>
      <p className="muted small">Среднее из оценок сюжета, персонажей и стиля.</p>
      {error && <p className="form-error">{error}</p>}
      <div className="form-actions">
        <button className="btn btn-primary" type="submit" disabled={saving}>
          {saving ? "Сохраняю…" : saved ? "Обновить оценку" : "Сохранить оценку"}
        </button>
        {message && <span className="muted">{message}</span>}
      </div>
>>>>>>> 088ebc434e4e609566051a7126e169906afacece
    </form>
  );
}

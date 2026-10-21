import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { api, getErrorMessage } from "../api/client";
import type { Rating } from "../types";

interface Props {
  entryId: number;
  onSaved?: (rating: Rating) => void;
}

const CRITERIA = [
  { key: "plot", label: "Сюжет" },
  { key: "characters", label: "Персонажи" },
  { key: "style", label: "Стиль" },
] as const;

type Values = Record<(typeof CRITERIA)[number]["key"], number>;

export default function RatingForm({ entryId, onSaved }: Props) {
  const [values, setValues] = useState<Values>({ plot: 7, characters: 7, style: 7 });
  const [saved, setSaved] = useState(false); // есть ли уже сохранённая оценка
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Общая оценка — среднее трёх критериев, пересчитывается прямо при движении ползунков
  // (на сервере считается так же: (сюжет + персонажи + стиль) / 3).
  const average = (values.plot + values.characters + values.style) / 3;

  // Подгружаем уже выставленную оценку (404 — значит оценки ещё нет)
  useEffect(() => {
    api
      .get<Rating>(`/library/${entryId}/rating`)
      .then(({ data }) => {
        setValues({ plot: data.plot, characters: data.characters, style: data.style });
        setSaved(true);
      })
      .catch(() => setSaved(false));
  }, [entryId]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const { data } = await api.put<Rating>(`/library/${entryId}/rating`, values);
      setSaved(true);
      setMessage("Оценка сохранена");
      onSaved?.(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="rating-form" onSubmit={handleSubmit}>
      <h3>Моя оценка</h3>
      {CRITERIA.map(({ key, label }) => (
        <label key={key} className="rating-row">
          <span>{label}</span>
          <input
            type="range"
            min={1}
            max={10}
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
    </form>
  );
}

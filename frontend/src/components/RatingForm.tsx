
import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { api, getErrorMessage } from "../api/client";
import type { Rating, ReadingStatus } from "../types";

interface Props {
  bookId: number;
  status: ReadingStatus;
  onSaved?: () => void;
}

const CRITERIA = [
  { key: "plot", label: "Сюжет" },
  { key: "characters", label: "Персонажи" },
  { key: "style", label: "Язык и стиль" },
] as const;

type Values = Record<(typeof CRITERIA)[number]["key"], number>;

export default function RatingForm({ bookId, status, onSaved }: Props) {
  const [values, setValues] = useState<Values>({
    plot: 7,
    characters: 7,
    style: 7,
  });
  const [saved, setSaved] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const locked = status !== "read";
  const average = (values.plot + values.characters + values.style) / 3;

  useEffect(() => {
    let cancelled = false;

    api
      .get<Rating>(`/books/${bookId}/rating`)
      .then(({ data }) => {
        if (cancelled) return;

        setValues({
          plot: data.plot,
          characters: data.characters,
          style: data.style,
        });
        setSaved(true);
      })
      .catch(() => {
        if (!cancelled) setSaved(false);
      });

    return () => {
      cancelled = true;
    };
  }, [bookId]);

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    if (locked || saving) return;

    setSaving(true);
    setError(null);
    setMessage(null);

    try {
      await api.post(`/books/${bookId}/rating`, values);
      setSaved(true);
      setMessage("Оценка сохранена");
      onSaved?.();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <form className="rating-form" onSubmit={handleSubmit}>
      <h3>Моя оценка</h3>

      {locked && (
        <p className="banner banner-info">
          Оценка доступна, когда у книги статус «Прочитано».
          {saved && " Ранее выставленная оценка показана ниже."}
        </p>
      )}

      {CRITERIA.map(({ key, label }) => (
        <label key={key} className="rating-row">
          <span>{label}</span>
          <input
            type="range"
            min={1}
            max={10}
            step={1}
            disabled={locked || saving}
            value={values[key]}
            onChange={(e) => {
              setValues((current) => ({
                ...current,
                [key]: Number(e.target.value),
              }));
              setMessage(null);
            }}
          />
          <strong>{values[key]}</strong>
        </label>
      ))}

      <p className="overall-score">
        Итоговая оценка: <strong>{average.toFixed(1)}</strong> / 10
      </p>

      <p className="muted small">
        Среднее из оценок сюжета, персонажей и языка и стиля.
      </p>

      {error && <p className="form-error">{error}</p>}

      {!locked && (
        <div className="form-actions">
          <button
            className="btn btn-primary"
            type="submit"
            disabled={saving}
          >
            {saving
              ? "Сохраняю…"
              : saved
                ? "Обновить оценку"
                : "Сохранить оценку"}
          </button>

          {message && <span className="muted">{message}</span>}
        </div>
      )}
    </form>
  );
}

interface Props {
  total: number;
  limit: number;
  offset: number;
  onChange: (offset: number) => void;
}

export default function Pagination({ total, limit, offset, onChange }: Props) {
  const pages = Math.max(1, Math.ceil(total / limit));
  const current = Math.floor(offset / limit) + 1;
  if (total <= limit) return null;

  return (
    <nav className="pagination" aria-label="Постраничная навигация">
      <button className="btn btn-outline btn-sm" disabled={current <= 1} onClick={() => onChange(offset - limit)}>
        ← Назад
      </button>
      <span className="muted">
        Страница {current} из {pages} · всего {total}
      </span>
      <button className="btn btn-outline btn-sm" disabled={current >= pages} onClick={() => onChange(offset + limit)}>
        Вперёд →
      </button>
    </nav>
  );
}

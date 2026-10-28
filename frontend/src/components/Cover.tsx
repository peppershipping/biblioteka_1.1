import { useState } from "react";

interface Props {
  url: string | null;
  title: string;
  large?: boolean;
}

/** Обложка книги; если ссылки нет или картинка не загрузилась — заглушка с первой буквой. */
export default function Cover({ url, title, large }: Props) {
  const [failed, setFailed] = useState(false);
  const className = "cover" + (large ? " cover-large" : "");

  if (url && !failed) {
    return (
      <div className={className}>
        <img src={url} alt={`Обложка: ${title}`} loading="lazy" onError={() => setFailed(true)} />
      </div>
    );
  }
  return (
    <div className={className} aria-hidden="true">
      <span>{title.trim().charAt(0).toUpperCase()}</span>
    </div>
  );
}

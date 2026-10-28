"""
Ядро рекомендательной системы (ТЗ раздел 9): контентная фильтрация.

Каждая книга описывается текстом (название + описание + жанры + авторы),
который переводится в числовой вектор TF-IDF. Профиль пользователя — среднее
векторов его оценённых книг: высокие оценки тянут профиль к себе, низкие —
отталкивают. Кандидаты ранжируются по косинусной близости к профилю.

Модуль не зависит от БД и FastAPI — только sklearn/numpy, поэтому его легко
тестировать.
"""

from dataclasses import dataclass, field

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

LIKE_THRESHOLD = 7.0      # итоговая оценка >= 7 — книга понравилась
DISLIKE_THRESHOLD = 4.0   # итоговая оценка <= 4 — не понравилась
DISLIKE_PENALTY = 0.5     # вес «антипрофиля» при вычитании близости


@dataclass
class BookDoc:
    id: int
    title: str
    description: str = ""
    authors: list[str] = field(default_factory=list)
    genres: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        # Жанры и авторов повторяем: так они весят больше обычных слов описания
        meta = " ".join(self.genres + self.authors)
        return f"{self.title} {self.description or ''} {meta} {meta}"


@dataclass
class Ranked:
    book_id: int
    score: float
    similar_to_id: int | None
    shared_genres: list[str]


def profile_weight(total: float) -> float:
    """Вес книги в профиле по итоговой оценке: >0 — нравится, <0 — не нравится, 0 — нейтрально."""
    if total >= LIKE_THRESHOLD:
        return total - (LIKE_THRESHOLD - 1)        # 7 -> 1 ... 10 -> 4
    if total <= DISLIKE_THRESHOLD:
        return -(DISLIKE_THRESHOLD + 1 - total)    # 4 -> -1 ... 1 -> -4
    return 0.0


def _weighted_mean(matrix, weights: np.ndarray):
    weights = np.abs(weights)
    summed = np.asarray(matrix.multiply(weights.reshape(-1, 1)).sum(axis=0))
    return summed / weights.sum()


def rank(candidates: list[BookDoc], profile: list[tuple[BookDoc, float]], limit: int = 100) -> list[Ranked]:
    """
    candidates — книги, из которых выбираем (без уже прочитанных/отклонённых);
    profile — [(книга, вес)] из profile_weight(); нулевые веса игнорируются.
    Возвращает кандидатов по убыванию близости к вкусам пользователя.
    """
    liked = [(d, w) for d, w in profile if w > 0]
    disliked = [(d, w) for d, w in profile if w < 0]
    if not candidates or not liked:
        return []

    docs = candidates + [d for d, _ in liked] + [d for d, _ in disliked]
    matrix = TfidfVectorizer(max_features=5000, sublinear_tf=True).fit_transform(d.text for d in docs)

    n_cand, n_liked = len(candidates), len(liked)
    cand_m = matrix[:n_cand]
    liked_m = matrix[n_cand : n_cand + n_liked]
    disliked_m = matrix[n_cand + n_liked :]

    liked_profile = _weighted_mean(liked_m, np.array([w for _, w in liked], dtype=float))
    scores = cosine_similarity(liked_profile, cand_m)[0]

    if disliked:
        dis_profile = _weighted_mean(disliked_m, np.array([w for _, w in disliked], dtype=float))
        scores = scores - DISLIKE_PENALTY * cosine_similarity(dis_profile, cand_m)[0]

    nearest = cosine_similarity(cand_m, liked_m).argmax(axis=1)  # ближайшая понравившаяся книга
    liked_genres = {g for d, _ in liked for g in d.genres}

    result = []
    for i, cand in enumerate(candidates):
        if scores[i] <= 0:
            continue
        result.append(
            Ranked(
                book_id=cand.id,
                score=round(float(scores[i]), 4),
                similar_to_id=liked[int(nearest[i])][0].id,
                shared_genres=[g for g in cand.genres if g in liked_genres],
            )
        )
    result.sort(key=lambda r: (-r.score, r.book_id))
    return result[:limit]

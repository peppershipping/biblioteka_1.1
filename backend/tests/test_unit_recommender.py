from app.services.recommender_engine import BookDoc, profile_weight, rank


def doc(i, title, genres, desc="", authors=()):
    return BookDoc(id=i, title=title, description=desc, genres=list(genres), authors=list(authors))


FANTASY_LIKED = doc(1, "Хоббит", ["Фэнтези"], "дракон гномы магия путешествие", ["Толкин"])
SCIFI_LIKED = doc(2, "Дюна", ["Научная фантастика"], "космос пустыня политика", ["Герберт"])


def test_profile_weight_thresholds():
    assert profile_weight(10) == 4
    assert profile_weight(7) == 1
    assert profile_weight(5.5) == 0
    assert profile_weight(4) == -1
    assert profile_weight(1) == -4


def test_similar_book_ranks_first():
    candidates = [
        doc(10, "Властелин колец", ["Фэнтези"], "кольцо магия эльфы путешествие", ["Толкин"]),
        doc(11, "Кулинарная книга", ["Кулинария"], "рецепты супы десерты"),
        doc(12, "Основание", ["Научная фантастика"], "империя космос будущее", ["Азимов"]),
    ]
    result = rank(candidates, [(FANTASY_LIKED, 4)])
    assert result[0].book_id == 10
    assert result[0].similar_to_id == 1
    assert result[0].shared_genres == ["Фэнтези"]
    assert 11 not in [r.book_id for r in result]  # нет общего с профилем — не рекомендуем


def test_nearest_liked_book_is_reported():
    candidates = [doc(12, "Основание", ["Научная фантастика"], "империя космос будущее", ["Азимов"])]
    result = rank(candidates, [(FANTASY_LIKED, 4), (SCIFI_LIKED, 4)])
    assert result[0].similar_to_id == 2


def test_disliked_books_push_similar_candidates_down():
    candidates = [
        doc(20, "Фэнтези А", ["Фэнтези"], "магия дракон"),
        doc(21, "Научная фантастика Б", ["Научная фантастика"], "космос империя"),
    ]
    liked_only = {r.book_id: r.score for r in rank(candidates, [(FANTASY_LIKED, 3), (SCIFI_LIKED, 3)])}
    with_dislike = {
        r.book_id: r.score
        for r in rank(candidates, [(FANTASY_LIKED, 3), (SCIFI_LIKED, 3), (doc(3, "Плохое фэнтези", ["Фэнтези"], "магия дракон"), -4)])
    }
    assert with_dislike.get(20, 0) < liked_only[20]


def test_empty_inputs_return_empty_list():
    assert rank([], [(FANTASY_LIKED, 4)]) == []
    assert rank([doc(1, "x", [])], []) == []
    assert rank([doc(1, "x", [])], [(FANTASY_LIKED, -4)]) == []  # одни антипримеры — рекомендовать нечего


def test_limit_and_deterministic_order():
    candidates = [doc(100 + i, f"Фэнтези {i}", ["Фэнтези"], "магия дракон") for i in range(10)]
    first = rank(candidates, [(FANTASY_LIKED, 4)], limit=5)
    second = rank(candidates, [(FANTASY_LIKED, 4)], limit=5)
    assert len(first) == 5
    assert [r.book_id for r in first] == [r.book_id for r in second]

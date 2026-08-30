from server.ui_results import _enrich_student_questions_from_repo
from shared.parser import calculate_score


def test_enrich_student_questions_subset():
    # 50 questions in repository
    repo_questions = [
        {
            "number": i,
            "text": f"Вопрос {i}",
            "answers": [
                {"text": f"Верно {i}", "correct": True},
                {"text": f"Неверно {i}", "correct": False},
            ],
            "multiple": False,
        }
        for i in range(1, 51)
    ]

    # Student took only a 10-question subset (e.g. questions 5..14)
    student_snapshot = [
        {
            "number": idx + 1,
            "text": f"Вопрос {i}",
            "answers": [f"Верно {i}", f"Неверно {i}"],
            "multiple": False,
        }
        for idx, i in enumerate(range(5, 15))
    ]

    # Student answered first 2 correctly, remaining 8 incorrectly
    student_answers = {1: ["Верно 5"], 2: ["Верно 6"]}
    for idx in range(3, 11):
        q_orig_num = idx + 4
        student_answers[idx] = [f"Неверно {q_orig_num}"]

    enriched = _enrich_student_questions_from_repo(student_snapshot, repo_questions)
    assert len(enriched) == 10
    for idx, q in enumerate(enriched):
        assert q["number"] == idx + 1
        assert any(a.get("correct") for a in q["answers"])

    score = calculate_score(enriched, student_answers, partial_multiple=True)
    assert score == "2/10"

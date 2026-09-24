from evaluation.evaluate import score


def test_evaluation_counts_detection_and_false_positives():
    expected = [{"file_path": "a.py", "category": "security", "severity": "high"}]
    actual = [
        {"file_path": "a.py", "category": "security", "severity": "high"},
        {"file_path": "b.py", "category": "style", "severity": "low"},
    ]
    result = score(expected, actual)
    assert result["detection_rate"] == 1.0
    assert result["false_positive_count"] == 1

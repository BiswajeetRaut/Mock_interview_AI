"""Coverage helpers — update weakness/strength maps from evaluation results."""


def update_coverage_from_evaluation(coverage: dict, evaluation: dict) -> dict:
    """Merge evaluation tags into coverage context. Returns updated coverage."""
    coverage = dict(coverage)  # don't mutate original

    weak = evaluation.get("topics_demonstrated_weak", [])
    strong = evaluation.get("topics_demonstrated_strong", [])

    existing_weak = list(coverage.get("weakness_tags", []))
    existing_strong = list(coverage.get("strength_tags", []))

    for tag in weak:
        if tag not in existing_weak:
            existing_weak.append(tag)
    for tag in strong:
        if tag not in existing_strong:
            existing_strong.append(tag)

    coverage["weakness_tags"] = existing_weak
    coverage["strength_tags"] = existing_strong
    return coverage

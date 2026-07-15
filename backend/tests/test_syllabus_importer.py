from pathlib import Path

from graduate_entrance.syllabus.importer import parse_syllabus_sources


def test_parse_syllabus_sources_preserves_raw_rows_and_separates_exam_blueprints() -> None:
    data = parse_syllabus_sources(Path("../seed/syllabus/raw"))

    assert data.source_row_count == 643
    assert len(data.subjects) == 4
    assert len(data.knowledge_points) == 641
    assert len(data.exam_blueprints) == 2
    assert len(data.exam_sections) == 2
    assert {subject.name for subject in data.subjects} == {"数学一", "408", "英语一", "政治"}


def test_parse_syllabus_sources_keeps_explicit_hierarchy_and_political_null_sections() -> None:
    data = parse_syllabus_sources(Path("../seed/syllabus/raw"))

    assert len(data.modules) == 16
    assert len(data.chapters) == 77
    assert len(data.sections) == 228
    assert sum(point.section_id is None for point in data.knowledge_points) == 59
    assert any(
        point.section_id is not None
        for point in data.knowledge_points
        if point.name.startswith("函数的概念")
    )


def test_parse_syllabus_sources_normalizes_requirement_without_losing_raw_text() -> None:
    data = parse_syllabus_sources(Path("../seed/syllabus/raw"))
    by_name = {point.name: point for point in data.knowledge_points}

    function_point = by_name["函数的概念与表示法（解析式、分段、隐式、参数式）"]
    derivative_point = by_name["导数的几何意义与物理意义；切线和法线方程"]

    assert function_point.requirement_raw == "理解"
    assert function_point.requirement_level == "understanding"
    assert derivative_point.requirement_raw == "会求"
    assert derivative_point.requirement_level == "application"
    assert derivative_point.requirement_actions == ["calculate"]


def test_parse_syllabus_sources_produces_stable_identifiers() -> None:
    first = parse_syllabus_sources(Path("../seed/syllabus/raw"))
    second = parse_syllabus_sources(Path("../seed/syllabus/raw"))

    assert [subject.id for subject in first.subjects] == [subject.id for subject in second.subjects]
    assert [point.id for point in first.knowledge_points] == [
        point.id for point in second.knowledge_points
    ]

from pathlib import Path

from app.db import session_scope
from app.db import init_db
from app.models import Project, Segment
from app.rendering import render_segment


def test_render_segment_accepts_filter_sensitive_caption(temp_storage):
    init_db()
    with session_scope() as session:
        project = Project(id="caption-test", status="awaiting_review")
        segment = Segment(
            id="caption-segment",
            project_id=project.id,
            title="Sensitive: title",
            rationale="test",
            start_ms=0,
            end_ms=1,
            caption_text="逗号, 分号; 引号' 结束\nsecond line: 100%",
        )
        session.add(project)
        session.add(segment)
    source = temp_storage / "source.mp4"
    source.write_bytes((Path(__file__).parent / "fixtures" / "sample.mp4").read_bytes())
    output = temp_storage / "renders" / "caption.mp4"
    output.parent.mkdir(parents=True)

    render_segment(source, output, segment)

    assert output.stat().st_size > 0
    assert not output.with_suffix(".caption.txt").exists()

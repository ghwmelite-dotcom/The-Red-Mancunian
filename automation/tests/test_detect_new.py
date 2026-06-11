import json

import detect_new


def test_new_ids_excludes_youtube_variants_and_known(tmp_path):
    for name in ("a.mp4", "a-youtube.mp4", "b.mp4", "b-youtube.mp4"):
        (tmp_path / name).write_bytes(b"")
    assert detect_new.new_ids(tmp_path, before={"a.mp4", "a-youtube.mp4"}) == ["b"]


def test_write_meta(tmp_path):
    detect_new.write_meta(tmp_path, run_id="99", ids=["b"],
                          rendered_at="2026-06-11T18:00:00+01:00")
    meta = json.loads((tmp_path / "meta.json").read_text())
    assert meta == {"run_id": "99", "story_ids": ["b"],
                    "rendered_at": "2026-06-11T18:00:00+01:00"}

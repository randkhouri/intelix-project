from pathlib import Path
from unittest.mock import patch

from reporter import ReportManager


def test_report_manager_save_writes_json_file(tmp_path: Path) -> None:
    manager = ReportManager(output_dir=tmp_path)
    out = manager.save("sample", {"ok": True, "score": 7})

    assert out == tmp_path / "sample.txt"
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert '"ok": true' in content
    assert '"score": 7' in content


def test_report_manager_save_returns_none_on_io_error(tmp_path: Path) -> None:
    manager = ReportManager(output_dir=tmp_path)
    with patch("reporter.open", side_effect=OSError("disk full")):
        out = manager.save("sample", {"ok": True})
    assert out is None

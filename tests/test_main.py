from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from main import _classify_file, collect_files_from_directory, main


def test_classify_file_supported_and_unsupported(tmp_path: Path) -> None:
    exe = tmp_path / "sample.exe"
    exe.write_bytes(b"MZ")
    doc = tmp_path / "sample.docx"
    doc.write_text("doc", encoding="utf-8")
    pdf = tmp_path / "sample.pdf"
    pdf.write_text("pdf", encoding="utf-8")
    txt = tmp_path / "sample.txt"
    txt.write_text("txt", encoding="utf-8")

    assert _classify_file(exe) == "exe"
    assert _classify_file(doc) == "word"
    assert _classify_file(pdf) == "pdf"
    assert _classify_file(txt) is None


def test_collect_files_caps_per_type_and_skips_unsupported(tmp_path: Path) -> None:
    # exe (2)
    (tmp_path / "a.exe").write_bytes(b"MZ")
    (tmp_path / "b.exe").write_bytes(b"MZ")
    # word (2)
    (tmp_path / "c.doc").write_text("doc", encoding="utf-8")
    (tmp_path / "d.docx").write_text("docx", encoding="utf-8")
    # pdf (2)
    (tmp_path / "e.pdf").write_text("pdf", encoding="utf-8")
    (tmp_path / "f.pdf").write_text("pdf", encoding="utf-8")
    # unsupported + subdir ignored
    (tmp_path / "g.txt").write_text("txt", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "h.exe").write_bytes(b"MZ")

    files, counts = collect_files_from_directory(tmp_path, max_per_type=1)

    assert counts == {"exe": 1, "word": 1, "pdf": 1}
    assert len(files) == 3
    labels = [label for label, _ in files]
    assert labels == ["exe", "word", "pdf"]


def test_collect_files_returns_empty_for_missing_directory(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    files, counts = collect_files_from_directory(missing, max_per_type=1)
    assert files == []
    assert counts == {}


def test_collect_files_returns_empty_for_non_directory(tmp_path: Path) -> None:
    file_path = tmp_path / "single.txt"
    file_path.write_text("hello", encoding="utf-8")
    files, counts = collect_files_from_directory(file_path, max_per_type=1)
    assert files == []
    assert counts == {}


def _args(tmp_path: Path, max_per_type: int = 20) -> SimpleNamespace:
    return SimpleNamespace(
        files_dir=str(tmp_path),
        output_dir=str(tmp_path / "out"),
        max_per_type=max_per_type,
        log_dir=str(tmp_path / "logs"),
        log_file="test.log",
    )


def test_main_returns_1_on_invalid_max_per_type(tmp_path: Path) -> None:
    args = _args(tmp_path, max_per_type=0)

    with (
        patch("main.parse_args", return_value=args),
        patch("main.validate_required_config"),
    ):
        assert main() == 1


def test_main_returns_2_on_partial_failures(tmp_path: Path) -> None:
    test_file = tmp_path / "sample.exe"
    test_file.write_bytes(b"MZ")
    args = _args(tmp_path)

    client = Mock()
    client.analyze_file.return_value = None

    with (
        patch("main.parse_args", return_value=args),
        patch("main.validate_required_config"),
        patch("main.IntelixClient", return_value=client),
    ):
        assert main() == 2

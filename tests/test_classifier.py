"""Tests for downloads_organizer.classifier module."""

from pathlib import Path
from unittest.mock import MagicMock

from downloads_organizer.classifier import (
    _classify_by_type,
    _format_size,
    _should_process,
    extract_content_preview,
)
from downloads_organizer.config import DEFAULT_CONFIG


class TestFormatSize:
    def test_bytes(self):
        assert _format_size(512) == "512.0 B"

    def test_kilobytes(self):
        assert _format_size(1024) == "1.0 KB"

    def test_megabytes(self):
        assert _format_size(1024 * 1024) == "1.0 MB"

    def test_gigabytes(self):
        assert _format_size(1024 * 1024 * 1024) == "1.0 GB"

    def test_fractional_kb(self):
        assert _format_size(1536) == "1.5 KB"


class TestShouldProcess:
    def test_ignores_ds_store(self):
        p = MagicMock(spec=Path)
        p.name = ".DS_Store"
        p.suffix = ""
        assert _should_process(p, DEFAULT_CONFIG) is False

    def test_ignores_crdownload(self):
        p = MagicMock(spec=Path)
        p.name = "file.crdownload"
        p.suffix = ".crdownload"
        assert _should_process(p, DEFAULT_CONFIG) is False

    def test_ignores_dotfiles(self):
        p = MagicMock(spec=Path)
        p.name = ".hidden_file"
        p.suffix = ""
        assert _should_process(p, DEFAULT_CONFIG) is False

    def test_ignores_tmp(self):
        p = MagicMock(spec=Path)
        p.name = "download.tmp"
        p.suffix = ".tmp"
        assert _should_process(p, DEFAULT_CONFIG) is False

    def test_allows_normal_pdf(self):
        p = MagicMock(spec=Path)
        p.name = "factura.pdf"
        p.suffix = ".pdf"
        assert _should_process(p, DEFAULT_CONFIG) is True

    def test_allows_normal_image(self):
        p = MagicMock(spec=Path)
        p.name = "photo.jpg"
        p.suffix = ".jpg"
        assert _should_process(p, DEFAULT_CONFIG) is True

    def test_ignores_thumbs_db(self):
        p = MagicMock(spec=Path)
        p.name = "Thumbs.db"
        p.suffix = ".db"
        assert _should_process(p, DEFAULT_CONFIG) is False


class TestClassifyByType:
    def test_pdf_returns_normal_priority(self, tmp_path):
        f = tmp_path / "informe.pdf"
        f.touch()
        result = _classify_by_type("documento", f, DEFAULT_CONFIG)
        assert result["priority"] == "normal"
        assert result["file_type"] == "documento"

    def test_filename_keyword_urgente(self, tmp_path):
        f = tmp_path / "factura_enero.pdf"
        f.touch()
        result = _classify_by_type("documento", f, DEFAULT_CONFIG)
        assert result["priority"] == "urgente"

    def test_filename_keyword_archivo(self, tmp_path):
        f = tmp_path / "backup_2022.zip"
        f.touch()
        result = _classify_by_type("comprimido", f, DEFAULT_CONFIG)
        assert result["priority"] == "archivo"

    def test_instalador_defaults_to_archivo(self, tmp_path):
        f = tmp_path / "setup.exe"
        f.touch()
        result = _classify_by_type("instalador", f, DEFAULT_CONFIG)
        assert result["priority"] == "archivo"

    def test_comprimido_defaults_to_archivo(self, tmp_path):
        f = tmp_path / "pack.zip"
        f.touch()
        result = _classify_by_type("comprimido", f, DEFAULT_CONFIG)
        assert result["priority"] == "archivo"

    def test_returns_dict_with_required_keys(self, tmp_path):
        f = tmp_path / "foto.jpg"
        f.touch()
        result = _classify_by_type("imagen", f, DEFAULT_CONFIG)
        assert "priority" in result
        assert "project" in result
        assert "file_type" in result

    def test_uses_first_configured_project(self, tmp_path):
        f = tmp_path / "doc.pdf"
        f.touch()
        config = {**DEFAULT_CONFIG, "projects": ["Trabajo", "Personal"]}
        result = _classify_by_type("documento", f, config)
        assert result["project"] == "Trabajo"

    def test_fallback_to_sin_clasificar_when_no_projects(self, tmp_path):
        f = tmp_path / "doc.pdf"
        f.touch()
        config = {**DEFAULT_CONFIG, "projects": []}
        result = _classify_by_type("documento", f, config)
        assert result["project"] == "Sin Clasificar"


class TestExtractContentPreview:
    def test_returns_text_for_txt_file(self, tmp_path):
        f = tmp_path / "hello.txt"
        f.write_text("Hello world", encoding="utf-8")
        result = extract_content_preview(f)
        assert result == "Hello world"

    def test_truncates_to_max_chars(self, tmp_path):
        f = tmp_path / "big.txt"
        f.write_text("A" * 5000, encoding="utf-8")
        result = extract_content_preview(f, max_chars=100)
        assert len(result) == 100

    def test_returns_empty_for_binary_file(self, tmp_path):
        f = tmp_path / "binary.bin"
        f.write_bytes(bytes(range(256)))
        result = extract_content_preview(f)
        assert result == ""

    def test_returns_empty_for_unsupported_extension(self, tmp_path):
        f = tmp_path / "archive.7z"
        f.write_bytes(b"\x37\x7A\xBC\xAF\x27\x1C")
        result = extract_content_preview(f)
        assert result == ""

    def test_reads_python_source(self, tmp_path):
        f = tmp_path / "script.py"
        f.write_text("def hello(): pass", encoding="utf-8")
        result = extract_content_preview(f)
        assert "def hello" in result

    def test_returns_empty_string_type(self, tmp_path):
        f = tmp_path / "image.png"
        f.write_bytes(b"\x89PNG\r\n\x1a\n")
        result = extract_content_preview(f)
        assert isinstance(result, str)
        assert result == ""

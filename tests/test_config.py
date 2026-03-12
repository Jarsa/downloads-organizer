"""Tests for downloads_organizer.config module."""

from pathlib import Path
from unittest.mock import patch

from downloads_organizer.config import (
    DEFAULT_CONFIG,
    _deep_merge,
    detect_file_type,
    load_config,
)


class TestLoadConfig:
    def test_returns_dict_with_expected_keys(self, tmp_path):
        """load_config() debe retornar un dict con las claves esperadas."""
        config_file = tmp_path / "config.yaml"
        with (
            patch("downloads_organizer.config.CONFIG_DIR", tmp_path),
            patch("downloads_organizer.config.CONFIG_FILE", config_file),
            patch("downloads_organizer.config.LOG_DIR", tmp_path),
        ):
            config = load_config()

        assert "downloads_folder" in config
        assert "ollama" in config
        assert "file_types" in config
        assert "projects" in config
        assert "classify_time" in config
        assert "organized_folder_name" in config
        assert "recent_folder_name" in config

    def test_returns_default_when_no_file(self, tmp_path):
        """Cuando no hay archivo de configuración se retornan los defaults."""
        config_file = tmp_path / "config.yaml"
        with (
            patch("downloads_organizer.config.CONFIG_DIR", tmp_path),
            patch("downloads_organizer.config.CONFIG_FILE", config_file),
            patch("downloads_organizer.config.LOG_DIR", tmp_path),
        ):
            config = load_config()

        assert config["ollama"]["model"] == DEFAULT_CONFIG["ollama"]["model"]
        assert config["classify_time"] == DEFAULT_CONFIG["classify_time"]

    def test_merges_user_config_with_defaults(self, tmp_path):
        """Valores del usuario deben sobreescribir defaults sin perder otras claves."""
        import yaml

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            yaml.dump({"ollama": {"model": "mistral"}}), encoding="utf-8"
        )
        with (
            patch("downloads_organizer.config.CONFIG_DIR", tmp_path),
            patch("downloads_organizer.config.CONFIG_FILE", config_file),
            patch("downloads_organizer.config.LOG_DIR", tmp_path),
        ):
            config = load_config()

        assert config["ollama"]["model"] == "mistral"
        # El resto de las claves de ollama se mantienen
        assert "timeout" in config["ollama"]
        assert "confidence_threshold" in config["ollama"]


class TestDetectFileType:
    def test_pdf_is_documento(self):
        assert detect_file_type(Path("factura.pdf"), DEFAULT_CONFIG) == "documento"

    def test_mp4_is_video(self):
        assert detect_file_type(Path("video.mp4"), DEFAULT_CONFIG) == "video"

    def test_xlsx_is_hoja_de_calculo(self):
        assert detect_file_type(Path("presupuesto.xlsx"), DEFAULT_CONFIG) == "hoja_de_calculo"

    def test_jpg_is_imagen(self):
        assert detect_file_type(Path("foto.jpg"), DEFAULT_CONFIG) == "imagen"

    def test_mp3_is_audio(self):
        assert detect_file_type(Path("cancion.mp3"), DEFAULT_CONFIG) == "audio"

    def test_py_is_codigo(self):
        assert detect_file_type(Path("script.py"), DEFAULT_CONFIG) == "codigo"

    def test_zip_is_comprimido(self):
        assert detect_file_type(Path("archivo.zip"), DEFAULT_CONFIG) == "comprimido"

    def test_unknown_extension_returns_otro(self):
        assert detect_file_type(Path("file.xyz"), DEFAULT_CONFIG) == "otro"

    def test_no_extension_returns_otro(self):
        assert detect_file_type(Path("Makefile"), DEFAULT_CONFIG) == "otro"

    def test_case_insensitive(self):
        assert detect_file_type(Path("FOTO.JPG"), DEFAULT_CONFIG) == "imagen"


class TestDeepMerge:
    def test_simple_override(self):
        base = {"a": 1, "b": 2}
        override = {"b": 99}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 99}

    def test_nested_merge_preserves_unoverridden_keys(self):
        base = {"ollama": {"model": "llama3.2", "timeout": 60}}
        override = {"ollama": {"model": "mistral"}}
        result = _deep_merge(base, override)
        assert result["ollama"]["model"] == "mistral"
        assert result["ollama"]["timeout"] == 60

    def test_adds_new_keys(self):
        base = {"a": 1}
        override = {"b": 2}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 2}

    def test_does_not_mutate_base(self):
        base = {"a": {"x": 1}}
        override = {"a": {"x": 2}}
        _deep_merge(base, override)
        assert base["a"]["x"] == 1

    def test_non_dict_value_overrides_dict(self):
        base = {"a": {"x": 1}}
        override = {"a": "string"}
        result = _deep_merge(base, override)
        assert result["a"] == "string"

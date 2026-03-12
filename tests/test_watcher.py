"""Tests for downloads_organizer.watcher module."""



from downloads_organizer.config import DEFAULT_CONFIG
from downloads_organizer.watcher import DownloadsHandler


def make_handler(tmp_path):
    """Crea un DownloadsHandler apuntando a tmp_path."""
    config = {
        **DEFAULT_CONFIG,
        "downloads_folder": str(tmp_path),
        "recent_folder_name": "Recien Descargado",
        "organized_folder_name": "Organizado",
        "notify_on_move": False,
    }
    return DownloadsHandler(config)


class TestShouldMove:
    def test_rejects_crdownload(self, tmp_path):
        handler = make_handler(tmp_path)
        f = tmp_path / "video.crdownload"
        f.touch()
        assert handler._should_move(f) is False

    def test_rejects_tmp(self, tmp_path):
        handler = make_handler(tmp_path)
        f = tmp_path / "file.tmp"
        f.touch()
        assert handler._should_move(f) is False

    def test_rejects_part(self, tmp_path):
        handler = make_handler(tmp_path)
        f = tmp_path / "file.part"
        f.touch()
        assert handler._should_move(f) is False

    def test_rejects_dotfile(self, tmp_path):
        handler = make_handler(tmp_path)
        f = tmp_path / ".hidden"
        f.touch()
        assert handler._should_move(f) is False

    def test_rejects_ds_store(self, tmp_path):
        handler = make_handler(tmp_path)
        f = tmp_path / ".DS_Store"
        f.touch()
        assert handler._should_move(f) is False

    def test_accepts_pdf(self, tmp_path):
        handler = make_handler(tmp_path)
        f = tmp_path / "documento.pdf"
        f.touch()
        assert handler._should_move(f) is True

    def test_accepts_zip(self, tmp_path):
        handler = make_handler(tmp_path)
        f = tmp_path / "archivo.zip"
        f.touch()
        assert handler._should_move(f) is True

    def test_accepts_image(self, tmp_path):
        handler = make_handler(tmp_path)
        f = tmp_path / "foto.jpg"
        f.touch()
        assert handler._should_move(f) is True


class TestIsManagedFolder:
    def test_file_in_recent_folder_is_managed(self, tmp_path):
        handler = make_handler(tmp_path)
        recent = tmp_path / "Recien Descargado"
        recent.mkdir(exist_ok=True)
        f = recent / "file.pdf"
        f.touch()
        assert handler._is_managed_folder(f) is True

    def test_file_in_organized_folder_is_managed(self, tmp_path):
        handler = make_handler(tmp_path)
        organized = tmp_path / "Organizado" / "Normal" / "Trabajo" / "documento"
        organized.mkdir(parents=True, exist_ok=True)
        f = organized / "file.pdf"
        f.touch()
        assert handler._is_managed_folder(f) is True

    def test_file_directly_in_downloads_is_not_managed(self, tmp_path):
        handler = make_handler(tmp_path)
        f = tmp_path / "newfile.pdf"
        f.touch()
        assert handler._is_managed_folder(f) is False

    def test_file_in_unrelated_subfolder_is_not_managed(self, tmp_path):
        handler = make_handler(tmp_path)
        other = tmp_path / "OtrasCarpetas"
        other.mkdir()
        f = other / "file.pdf"
        f.touch()
        assert handler._is_managed_folder(f) is False

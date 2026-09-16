from local_media_curator.app import create_app
from local_media_curator.ui.main_window import MainWindow


def main() -> None:
    app = create_app()
    window = MainWindow()
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()

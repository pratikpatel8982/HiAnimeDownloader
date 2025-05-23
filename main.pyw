# main.py (in your project root, e.g., HiAnimeDownloader/main.py)
import sys
import os
# This assumes your controller class AnimeDownloaderWindow is in gui/main_window.py
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# --- END OF MODIFICATION ---
try:
    from gui.main_window import AnimeDownloaderWindow
except ImportError as e:
    print(f"Error importing AnimeDownloaderWindow: {e}")
    sys.exit(1)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QApplication, QStyleFactory
from PyQt6.QtCore import QSettings, QFile, QTextStream, QIODevice # For reading QSS

# ... (QSettings keys, including new ones) ...
KEY_APP_STYLE = "interface/appStyle"
KEY_CUSTOM_QSS_THEME = "interface/customQssTheme"

def apply_app_appearance_settings(app: QApplication):
    settings = QSettings()

    # 1. Apply Application Style (Qt Style)
    app_style_name = settings.value(KEY_APP_STYLE, "Default (OS)", type=str)
    if app_style_name != "Default (OS)" and app_style_name in QStyleFactory.keys():
        try:
            style = QStyleFactory.create(app_style_name)
            if style:
                app.setStyle(style)
                print(f"[Appearance] Applied Qt Style: {app_style_name}")
        except Exception as e:
            print(f"[Appearance] Error applying Qt Style '{app_style_name}': {e}")
    else:
        print(f"[Appearance] Using default OS Qt Style (Requested: {app_style_name}).")

    # 2. Apply Custom QSS Theme (if selected)
    qss_file_path = settings.value(KEY_CUSTOM_QSS_THEME, "", type=str)
    if qss_file_path and os.path.exists(qss_file_path):
        try:
            file = QFile(qss_file_path)
            if file.open(QIODevice.OpenModeFlag.ReadOnly | QIODevice.OpenModeFlag.Text):
                stream = QTextStream(file)
                app.setStyleSheet(stream.readAll())
                file.close()
                print(f"[Appearance] Applied custom QSS theme: {qss_file_path}")
            else:
                print(f"[Appearance] Error: Could not open QSS file: {qss_file_path} - {file.errorString()}")
        except Exception as e:
            print(f"[Appearance] Error applying QSS theme from '{qss_file_path}': {e}")
    elif qss_file_path: # Path saved but file not found
        print(f"[Appearance] Warning: QSS theme file not found at '{qss_file_path}'.")
    else: # No custom QSS theme selected
        app.setStyleSheet("") # Clear any previous global stylesheet
        print(f"[Appearance] No custom QSS theme selected. Using style's default appearance.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setOrganizationName("pratikpatel8982")
    app.setApplicationName("HiAnimeDownloader")

    apply_app_appearance_settings(app) # Apply before creating main window

    from gui.main_window import AnimeDownloaderWindow
    main_window = AnimeDownloaderWindow()
    main_window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    app = QApplication(sys.argv)

    app.setOrganizationName("pratikpatel8982") # Replace with your name/org
    app.setApplicationName("HiAnimeDownloader")

    main_window = AnimeDownloaderWindow()
    main_window.show()

    sys.exit(app.exec())
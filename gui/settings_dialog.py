# gui/settings_dialog.py
import os
import shutil
import glob
import threading # Import threading for background tasks

from PyQt6.QtWidgets import (
    QDialog, QFileDialog, QMessageBox, QDialogButtonBox, QStyleFactory
)
from PyQt6.QtCore import QSettings, QStandardPaths, pyqtSignal, Qt # Import Qt
from PyQt6.QtGui import QPixmapCache # QPalette, QColor might not be needed now

from .ui_settings_dialog import Ui_SettingsDialog

# Define QSettings keys
KEY_DEFAULT_DOWNLOAD_PATH = "general/defaultDownloadPath"
KEY_DEFAULT_LANGUAGE = "general/defaultLanguage"
KEY_DEFAULT_QUALITY = "general/defaultQuality"
KEY_FFMPEG_PATH = "downloads/ffmpegPath"
KEY_DOWNLOAD_RETRIES = "downloads/downloadRetries"
# Add new keys for interface settings
KEY_APP_STYLE = "interface/appStyle"
KEY_CUSTOM_QSS_THEME = "interface/customQssTheme"
THEME_DIR = os.path.join(os.path.dirname(__file__), "themes") # Assumes themes/ is in gui/


class SettingsDialog(QDialog):

    def __init__(self, parent=None, anime_service=None): # Accept anime_service
        super().__init__(parent)
        self.settings = QSettings()
        self.anime_service = anime_service # Store the instance

        self.ui = Ui_SettingsDialog()
        self.ui.setupUi(self)

        self._populate_app_style_combo()
        self._populate_custom_theme_combo() # New method

        self._connect_signals()
        self.load_settings()

    def _populate_app_style_combo(self):
        #qt themes
        self.ui.app_style_combo.addItem("Default (OS)")
        styles = QStyleFactory.keys()
        for style in styles:
            self.ui.app_style_combo.addItem(style)

    def _populate_custom_theme_combo(self):
        #custom theme combo
        self.ui.custom_theme_combo.addItem("None (Use Application Style Only)") # Default option

        os.makedirs(THEME_DIR, exist_ok=True) # Ensure themes directory exists
        qss_files = glob.glob(os.path.join(THEME_DIR, "*.qss"))
        for qss_file_path in qss_files:
            theme_name = os.path.splitext(os.path.basename(qss_file_path))[0]
            # Store the full path as item data for easy loading later
            # Use underscores instead of spaces for internal storage if needed, but display friendly name
            display_name = theme_name.replace("_", " ").title()
            self.ui.custom_theme_combo.addItem(display_name, userData=qss_file_path)

    def _connect_signals(self):
        self.ui.browse_default_download_path_btn.clicked.connect(self._browse_default_download_path)
        self.ui.browse_ffmpeg_path_btn.clicked.connect(self._browse_ffmpeg_path)
        self.ui.recheck_ffmpeg_btn.clicked.connect(self._recheck_ffmpeg)
        self.ui.clear_image_cache_btn.clicked.connect(self._clear_image_cache)
        self.ui.reset_settings_btn.clicked.connect(self._reset_all_settings)

        self.ui.button_box.button(QDialogButtonBox.StandardButton.Ok).clicked.connect(self.accept)
        self.ui.button_box.button(QDialogButtonBox.StandardButton.Cancel).clicked.connect(self.reject)
        # Check if the Apply button exists before connecting
        apply_button = self.ui.button_box.button(QDialogButtonBox.StandardButton.Apply)
        if apply_button:
            apply_button.clicked.connect(self.apply_settings)

    def load_settings(self):
        # General
        default_dl_path_system = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
        app_dl_folder = os.path.join(default_dl_path_system, "HiAnime_Downloader_Downloads") if default_dl_path_system else \
                        os.path.join(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation) or os.path.expanduser("~"), "HiAnime_Downloader_Downloads")

        self.ui.default_download_path_edit.setText(self.settings.value(KEY_DEFAULT_DOWNLOAD_PATH, app_dl_folder, type=str))
        self.ui.default_language_combo.setCurrentText(self.settings.value(KEY_DEFAULT_LANGUAGE, "SUB", type=str))
        # Ensure items are present before setting, or handle gracefully
        qualities = [self.ui.default_quality_combo.itemText(i) for i in range(self.ui.default_quality_combo.count())]
        saved_quality = self.settings.value(KEY_DEFAULT_QUALITY, "1080p", type=str)
        if saved_quality in qualities:
            self.ui.default_quality_combo.setCurrentText(saved_quality)
        elif qualities: # Fallback to first item if saved not found
            self.ui.default_quality_combo.setCurrentIndex(0)

        # Downloads
        self.ui.ffmpeg_path_edit.setText(self.settings.value(KEY_FFMPEG_PATH, "", type=str))
        self.ui.download_retries_spinbox.setValue(self.settings.value(KEY_DOWNLOAD_RETRIES, 10, type=int))

        # Interface Settings
        current_app_style = self.settings.value(KEY_APP_STYLE, "Default (OS)", type=str)
        if self.ui.app_style_combo.findText(current_app_style) != -1:
            self.ui.app_style_combo.setCurrentText(current_app_style)
        else:
            self.ui.app_style_combo.setCurrentText("Default (OS)")

        saved_qss_path = self.settings.value(KEY_CUSTOM_QSS_THEME, "", type=str)
        if saved_qss_path:
            # Find the item index by user data (the saved path)
            idx = self.ui.custom_theme_combo.findData(saved_qss_path)
            if idx != -1:
                self.ui.custom_theme_combo.setCurrentIndex(idx)
            else: # Saved path not found, maybe file was deleted
                self.ui.custom_theme_combo.setCurrentIndex(0) # "None"
        else:
            self.ui.custom_theme_combo.setCurrentIndex(0) # "None"

        print("Settings loaded into dialog.")

    def save_settings(self):
        # General
        self.settings.setValue(KEY_DEFAULT_DOWNLOAD_PATH, self.ui.default_download_path_edit.text())
        self.settings.setValue(KEY_DEFAULT_LANGUAGE, self.ui.default_language_combo.currentText())
        self.settings.setValue(KEY_DEFAULT_QUALITY, self.ui.default_quality_combo.currentText())

        # Downloads
        self.settings.setValue(KEY_FFMPEG_PATH, self.ui.ffmpeg_path_edit.text())
        self.settings.setValue(KEY_DOWNLOAD_RETRIES, self.ui.download_retries_spinbox.value())

        # Interface Settings
        self.settings.setValue(KEY_APP_STYLE, self.ui.app_style_combo.currentText())

        current_idx = self.ui.custom_theme_combo.currentIndex()
        if current_idx > 0: # Not "None"
            qss_path = self.ui.custom_theme_combo.itemData(current_idx)
            self.settings.setValue(KEY_CUSTOM_QSS_THEME, qss_path)
        else: # "None" selected
            self.settings.setValue(KEY_CUSTOM_QSS_THEME, "") # Save empty string for no QSS

        self.settings.sync()
        print("Settings saved.")

    def apply_settings(self):
        self.save_settings()
        QMessageBox.information(self, "Settings Applied", "Settings have been applied. Some changes may require an application restart.")

    def accept(self):
        self.save_settings() # Save before accepting
        super().accept()

# --- SLOT METHODS ---
    def _browse_default_download_path(self):
        path = QFileDialog.getExistingDirectory(
            self, "Select Default Download Directory", self.ui.default_download_path_edit.text()
        )
        if path:
            self.ui.default_download_path_edit.setText(path)

    def _browse_ffmpeg_path(self):
            # Define the file filter string based on the operating system
            if os.name == 'nt':
                # Windows: Filter for .exe files specifically
                filter_string = "Executables (*.exe);;All files (*)"
            else:
                # Linux/macOS/Other: Offer a general "Executable files" description
                # and still include all files as executables might not have extensions
                filter_string = "Executable files (*);;All files (*)"

            path, _ = QFileDialog.getOpenFileName(
                self, "Select FFmpeg Executable", self.ui.ffmpeg_path_edit.text(), filter_string
            )
            if path:
                self.ui.ffmpeg_path_edit.setText(path)

    def _recheck_ffmpeg(self):
        # You might want to call a method in AnimeService to check for ffmpeg
        # For now, let's keep the shutil.which logic here as it's simple.
        ffmpeg_exe = shutil.which("ffmpeg")
        if ffmpeg_exe:
            self.ui.ffmpeg_path_edit.setText(ffmpeg_exe)
            QMessageBox.information(self, "FFmpeg Check", f"FFmpeg found in PATH: {ffmpeg_exe}")
        else:
            # Keep existing user path if any, just inform
            QMessageBox.warning(self, "FFmpeg Check", "FFmpeg not found in system PATH. Please specify the path manually if needed.")

    def _clear_image_cache(self):
        QPixmapCache.clear()
        QMessageBox.information(self, "Image Cache", "Image cache has been cleared.")

    def _reset_all_settings(self):
        reply = QMessageBox.warning(
            self, "Reset Settings",
            "Are you sure you want to reset all application settings to their defaults? This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            keys_to_reset = [
                KEY_DEFAULT_DOWNLOAD_PATH, KEY_DEFAULT_LANGUAGE, KEY_DEFAULT_QUALITY,
                KEY_FFMPEG_PATH, KEY_DOWNLOAD_RETRIES,
                KEY_APP_STYLE, KEY_CUSTOM_QSS_THEME,
                "last_language", "last_quality", "last_download_path", "log_visible",
                "window_geometry"
            ]
            for key in keys_to_reset:
                self.settings.remove(key)

            self.settings.sync()
            self.load_settings()
            QMessageBox.information(self, "Settings Reset", "All settings have been reset to default. Some changes may require an application restart.")
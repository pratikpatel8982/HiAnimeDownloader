# gui/ui_settings_dialog.py
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QLabel,QLineEdit,
    QPushButton, QComboBox, QSpinBox, QDialogButtonBox, QFormLayout
)
from PyQt6.QtCore import Qt, QCoreApplication

class Ui_SettingsDialog(object):
    def setupUi(self, SettingsDialogInstance):
        SettingsDialogInstance.setObjectName("SettingsDialogInstance")
        SettingsDialogInstance.setWindowTitle(QCoreApplication.translate("SettingsDialogInstance", "Settings"))
        SettingsDialogInstance.setMinimumSize(480, 320) # Adjusted minimum size

        self.main_layout = QVBoxLayout(SettingsDialogInstance)

        self.tab_widget = QTabWidget()
        self.main_layout.addWidget(self.tab_widget)

        # --- General Tab ---
        self.general_tab = QWidget()
        self.tab_widget.addTab(self.general_tab, QCoreApplication.translate("SettingsDialogInstance", "General"))
        general_layout = QFormLayout(self.general_tab)

        self.default_download_path_label = QLabel(QCoreApplication.translate("SettingsDialogInstance", "Default Download Path:"))
        self.default_download_path_edit = QLineEdit()
        self.browse_default_download_path_btn = QPushButton(QCoreApplication.translate("SettingsDialogInstance", "Browse..."))
        download_path_layout = QHBoxLayout()
        download_path_layout.addWidget(self.default_download_path_edit)
        download_path_layout.addWidget(self.browse_default_download_path_btn)
        general_layout.addRow(self.default_download_path_label, download_path_layout)

        self.default_language_label = QLabel(QCoreApplication.translate("SettingsDialogInstance", "Default Language:"))
        self.default_language_combo = QComboBox()
        self.default_language_combo.addItems(["SUB", "DUB"])
        general_layout.addRow(self.default_language_label, self.default_language_combo)

        self.default_quality_label = QLabel(QCoreApplication.translate("SettingsDialogInstance", "Default Quality:"))
        self.default_quality_combo = QComboBox()
        self.default_quality_combo.addItems(["1080p", "720p", "480p", "360p"])
        general_layout.addRow(self.default_quality_label, self.default_quality_combo)

        # --- Downloads Tab ---
        self.downloads_tab = QWidget()
        self.tab_widget.addTab(self.downloads_tab, QCoreApplication.translate("SettingsDialogInstance", "Downloads"))
        downloads_layout = QFormLayout(self.downloads_tab)

        self.ffmpeg_path_label = QLabel(QCoreApplication.translate("SettingsDialogInstance", "FFmpeg Path:"))
        self.ffmpeg_path_edit = QLineEdit()
        self.ffmpeg_path_edit.setPlaceholderText(QCoreApplication.translate("SettingsDialogInstance", "Auto-detect or specify path to ffmpeg executable"))
        self.browse_ffmpeg_path_btn = QPushButton(QCoreApplication.translate("SettingsDialogInstance", "Browse..."))
        ffmpeg_path_layout = QHBoxLayout()
        ffmpeg_path_layout.addWidget(self.ffmpeg_path_edit)
        ffmpeg_path_layout.addWidget(self.browse_ffmpeg_path_btn)
        downloads_layout.addRow(self.ffmpeg_path_label, ffmpeg_path_layout)

        self.recheck_ffmpeg_btn = QPushButton(QCoreApplication.translate("SettingsDialogInstance", "Re-check FFmpeg in PATH"))
        downloads_layout.addRow(self.recheck_ffmpeg_btn)

        self.download_retries_label = QLabel(QCoreApplication.translate("SettingsDialogInstance", "Download Retries:"))
        self.download_retries_spinbox = QSpinBox()
        self.download_retries_spinbox.setRange(1, 100)
        self.download_retries_spinbox.setValue(10)
        downloads_layout.addRow(self.download_retries_label, self.download_retries_spinbox)
        
        # --- Interface Tab --- (ON HOLD - Commented out or removed) ---
        self.interface_tab = QWidget()
        self.tab_widget.addTab(self.interface_tab, QCoreApplication.translate("SettingsDialogInstance", "Interface"))
        interface_layout = QFormLayout(self.interface_tab)

        self.app_style_label = QLabel(QCoreApplication.translate("SettingsDialogInstance", "Application Style (requires restart):"))
        self.app_style_combo = QComboBox() # Was theme_combo
        # Styles will be populated dynamically (QStyleFactory.keys())
        interface_layout.addRow(self.app_style_label, self.app_style_combo)

        self.custom_theme_label = QLabel(QCoreApplication.translate("SettingsDialogInstance", "Custom Theme (QSS, requires restart):"))
        self.custom_theme_combo = QComboBox() # For selecting .qss files
        interface_layout.addRow(self.custom_theme_label, self.custom_theme_combo)

        # ... (assign self.app_style_combo, self.custom_theme_combo to SettingsDialogInstance) ...
        SettingsDialogInstance.app_style_combo = self.app_style_combo
        SettingsDialogInstance.custom_theme_combo = self.custom_theme_combo

        # --- Maintenance Tab ---
        self.maintenance_tab = QWidget()
        self.tab_widget.addTab(self.maintenance_tab, QCoreApplication.translate("SettingsDialogInstance", "Maintenance"))
        maintenance_layout = QVBoxLayout(self.maintenance_tab)

        self.check_plugin_update_btn = QPushButton(QCoreApplication.translate("SettingsDialogInstance", "Check for Plugin Updates"))
        maintenance_layout.addWidget(self.check_plugin_update_btn)

        self.clear_image_cache_btn = QPushButton(QCoreApplication.translate("SettingsDialogInstance", "Clear Image Cache"))
        maintenance_layout.addWidget(self.clear_image_cache_btn)

        self.reset_settings_btn = QPushButton(QCoreApplication.translate("SettingsDialogInstance", "Reset All Settings to Default"))
        maintenance_layout.addWidget(self.reset_settings_btn)
        maintenance_layout.addStretch()

        # --- Standard Buttons ---
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Apply
        )
        self.main_layout.addWidget(self.button_box)

        # Assign widgets to instance for direct access
        SettingsDialogInstance.tab_widget = self.tab_widget
        SettingsDialogInstance.default_download_path_edit = self.default_download_path_edit
        SettingsDialogInstance.browse_default_download_path_btn = self.browse_default_download_path_btn
        SettingsDialogInstance.default_language_combo = self.default_language_combo
        SettingsDialogInstance.default_quality_combo = self.default_quality_combo
        SettingsDialogInstance.ffmpeg_path_edit = self.ffmpeg_path_edit
        SettingsDialogInstance.browse_ffmpeg_path_btn = self.browse_ffmpeg_path_btn
        SettingsDialogInstance.recheck_ffmpeg_btn = self.recheck_ffmpeg_btn
        SettingsDialogInstance.download_retries_spinbox = self.download_retries_spinbox
        SettingsDialogInstance.check_plugin_update_btn = self.check_plugin_update_btn
        SettingsDialogInstance.clear_image_cache_btn = self.clear_image_cache_btn
        SettingsDialogInstance.reset_settings_btn = self.reset_settings_btn
        SettingsDialogInstance.button_box = self.button_box

        self.retranslateUi(SettingsDialogInstance)
        self.tab_widget.setCurrentIndex(0)

    def retranslateUi(self, SettingsDialogInstance):
        pass # For future translations
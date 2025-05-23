# gui/ui_about_dialog.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDialogButtonBox, QSizePolicy, QSpacerItem
)
from PyQt6.QtCore import Qt, QCoreApplication


class Ui_AboutDialog(object):
    def setupUi(self, AboutDialogInstance):
        AboutDialogInstance.setObjectName("AboutDialog")
        AboutDialogInstance.setWindowTitle(QCoreApplication.translate("AboutDialog", "About HiAnime Downloader"))
        AboutDialogInstance.setMinimumSize(350, 200)
        AboutDialogInstance.setModal(True) # Make it a modal dialog

        self.main_layout = QVBoxLayout(AboutDialogInstance)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(10)

        # --- Application Name ---
        self.app_name_label = QLabel(AboutDialogInstance)
        self.app_name_label.setObjectName("app_name_label")
        font = self.app_name_label.font()
        font.setPointSize(16)
        font.setBold(True)
        self.app_name_label.setFont(font)
        self.app_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.app_name_label)

        # --- Version Label ---
        self.version_label = QLabel(AboutDialogInstance)
        self.version_label.setObjectName("version_label")
        font = self.version_label.font()
        font.setPointSize(10)
        self.version_label.setFont(font)
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.version_label)

        # --- Author Label ---
        self.author_label = QLabel(AboutDialogInstance)
        self.author_label.setObjectName("author_label")
        self.author_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.author_label)

        self.main_layout.addSpacing(15) # Add some space

        # --- Repository Link ---
        # Using a QLabel with openExternalLinks enabled to make URL clickable
        self.repo_link_label = QLabel(AboutDialogInstance)
        self.repo_link_label.setObjectName("repo_link_label")
        self.repo_link_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.repo_link_label.setOpenExternalLinks(True) # Make links clickable
        self.repo_link_label.setTextFormat(Qt.TextFormat.RichText) # Enable HTML for links
        self.main_layout.addWidget(self.repo_link_label)

        # Spacer to push buttons to the bottom
        vertical_spacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.main_layout.addItem(vertical_spacer)

        # --- Button Box ---
        self.button_box = QDialogButtonBox(AboutDialogInstance)
        self.button_box.setObjectName("button_box")
        self.button_box.setOrientation(Qt.Orientation.Horizontal)
        self.button_box.setStandardButtons(QDialogButtonBox.StandardButton.Ok)
        self.main_layout.addWidget(self.button_box)

        # --- Assign widgets to instance for direct access ---
        AboutDialogInstance.app_name_label = self.app_name_label
        AboutDialogInstance.version_label = self.version_label
        AboutDialogInstance.author_label = self.author_label
        AboutDialogInstance.repo_link_label = self.repo_link_label
        AboutDialogInstance.button_box = self.button_box

        self.retranslateUi(AboutDialogInstance)


    def retranslateUi(self, AboutDialogInstance):
        _translate = QCoreApplication.translate
        # These will be dynamically set by the AboutDialog class,
        # but provide initial placeholder for designer perspective.
        self.app_name_label.setText(_translate("AboutDialog", "HiAnime Downloader"))
        self.version_label.setText(_translate("AboutDialog", "Version: vX.Y.Z"))
        self.author_label.setText(_translate("AboutDialog", "Developed by: Pratik Patel"))
        self.repo_link_label.setText(_translate("AboutDialog", "Project Repository: <a href=\"https://github.com/pratikpatel8982/HiAnimeDownloadeR\">GitHub</a>"))
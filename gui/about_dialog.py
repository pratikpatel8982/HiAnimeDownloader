# gui/about_dialog.py
from PyQt6.QtWidgets import QDialog, QMessageBox
from PyQt6.QtCore import QCoreApplication, Qt, QUrl # Import QUrl for opening links

from .ui_about_dialog import Ui_AboutDialog
import version # Import the version module from the project root

# Define the repository URL
REPO_URL = "https://github.com/pratikpatel8982/HiAnimeDownloader"

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_AboutDialog()
        self.ui.setupUi(self)

        self._populate_info()
        self._connect_signals()

    def _populate_info(self):
        """Populates the labels in the About dialog with dynamic information."""
        _translate = QCoreApplication.translate

        self.ui.app_name_label.setText(_translate("AboutDialog", "HiAnime Downloader"))
        self.ui.version_label.setText(_translate("AboutDialog", f"Version: v{version.__version__}"))
        self.ui.author_label.setText(_translate("AboutDialog", "Developed by: Pratik Patel"))
        
        # Set the repository link, making it clickable
        self.ui.repo_link_label.setText(
            _translate("AboutDialog", f"Project Repository: <a href=\"{REPO_URL}\">GitHub</a>")
        )
        self.ui.repo_link_label.setOpenExternalLinks(True) # Ensure links are clickable
        self.ui.repo_link_label.setTextFormat(Qt.TextFormat.RichText) # Enable HTML rendering

    def _connect_signals(self):
        """Connects signals to slots for the About dialog."""
        # Connect the Ok button in the button box to close the dialog
        self.ui.button_box.accepted.connect(self.accept)
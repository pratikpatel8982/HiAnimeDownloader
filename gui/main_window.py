import os
import threading

# --- Qt Imports ---
from PyQt6.QtWidgets import (
    QApplication, QWidget, QMessageBox, QFileDialog, 
    QTableWidgetItem, QLabel, QMenu
)
from PyQt6.QtGui import (
    QTextCursor, QAction, QDesktopServices, QPixmap, QPixmapCache
)
from PyQt6.QtCore import (
    pyqtSignal, Qt, QSettings, QStandardPaths, QUrl, QSize, QByteArray,QSignalBlocker
)
from PyQt6.QtNetwork import (
    QNetworkAccessManager, QNetworkRequest, QNetworkReply
)

from downloader.anime_service import AnimeService 

# --- UI Definition and Helpers Import ---
from .ui_main_window import UiMainWindow
from .helpers import NumericTableWidgetItem, strip_ansi_codes

# --- Settings Dialog Import ---
from .settings_dialog import SettingsDialog # <-- IMPORT THE NEW DIALOG
from .settings_dialog import ( # <-- IMPORT THE KEYS (good practice)
    KEY_DEFAULT_DOWNLOAD_PATH, KEY_DEFAULT_LANGUAGE, KEY_DEFAULT_QUALITY,
    KEY_FFMPEG_PATH, KEY_DOWNLOAD_RETRIES
)

from .about_dialog import AboutDialog

class AnimeDownloaderWindow(QWidget):
    # --- Signals ---
    output_signal = pyqtSignal(str)
    search_finished_signal = pyqtSignal()
    update_episode_title_signal = pyqtSignal(str)
    update_episode_progress_signal = pyqtSignal(int)
    update_batch_progress_signal = pyqtSignal(int, int)
    set_download_button_enabled_signal = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._initialize_app_state_and_config() # Step 1: Basic attributes, settings
        
        self.anime_service = AnimeService()      # Step 2: Initialize backend service

        self.anime_service.set_gui_logger_callback(self.output_signal.emit, log_debug_to_gui=False)

        # Step 3: Setup the UI using the UiMainWindow class
        # The UiMainWindow class will create widgets and assign them as attributes to 'self'
        self.ui_setup = UiMainWindow() 
        self.ui_setup.setupUi(self)

        self._restore_window_geometry()
        self._connect_all_signals()          # Step 4: Connect UI element signals to controller methods
        self._load_and_apply_settings_to_ui()# Step 5: Load saved settings and update UI
        self._apply_initial_ui_visibility_state() # Step 6: Set initial visibility of UI groups

        self._check_ffmpeg_on_startup()

    def _check_ffmpeg_on_startup(self):
        """Checks for FFmpeg using the service and informs user if not found by initial check."""
        if not self.anime_service.is_ffmpeg_available(): # Use the method from AnimeService
            ffmpeg_builds_url = "https://github.com/yt-dlp/FFmpeg-Builds"

            # Constructing the message based on your provided structure
            dialog_title = "FFmpeg Not Found" # Intended title
            
            # Main text content, incorporating the URL directly
            dialog_text = (
                "FFmpeg could not be found in your system's PATH by an initial check.\n\n"
                "For full functionality, such as embedding subtitles and some format conversions, "
                "FFmpeg is required. Downloads might still work, but these post-processing steps could fail.\n\n"
                f"Please install FFmpeg (e.g., from {ffmpeg_builds_url}) and ensure it's added to your system's PATH, "
                "or place the ffmpeg executable in the application's directory.\n\n" # Corrected f-string placement
                "The application will attempt to proceed, and yt-dlp will issue specific errors "
                "if it cannot find FFmpeg when needed."
            )
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle(dialog_title)
            msg_box.setText(dialog_text)
            msg_box.setTextFormat(Qt.TextFormat.MarkdownText) # Allows for basic formatting if needed, or use PlainText
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()

    def _initialize_app_state_and_config(self):
        """Initialize non-UI attributes, settings objects, network managers, etc."""
        self.selected_anime_data = None
        self.anime_results = [] # Stores results from anime_service.search_anime
        self.table_thumbnail_size = QSize(80, 120) # Default, used by UiMainWindow and image loading
        self.is_download_active = False
        self.video_extensions = ('.mp4', '.mkv', '.webm', '.flv', '.avi', '.mov', '.wmv', '.ts')
        
        # For progress tracking
        self.current_episode_last_pct = 0.0
        self.total_episodes_in_batch = 0
        self.completed_episodes_in_batch = 0
        self.current_tracking_video_file = None

        # QSettings for persistence
        self.settings = QSettings() # IMPORTANT: Use consistent names

        # Network manager for image loading
        self.network_manager = QNetworkAccessManager(self)
        self.pixmap_cache = QPixmapCache()
        self.pixmap_cache.setCacheLimit(100 * 1024) # Cache limit e.g., 100MB
        self.active_image_requests = {} # For tracking image download replies

    def open_settings_dialog(self):
        """Opens the settings dialog."""
        settings_dialog = SettingsDialog(self, self.anime_service)
        # SettingsDialog uses QSettings directly, so main_window doesn't need to pass settings.
        
        if settings_dialog.exec(): # exec() is modal (blocks until dialog is closed)
            # "OK" or "Apply" (via OK) was clicked in the SettingsDialog.
            # SettingsDialog's accept() method calls save_settings().
            # Now, apply any settings that affect the main window's behavior or UI.
            self._apply_main_window_relevant_settings()
            
            # You might still want to inform the user if a restart is needed for some settings,
            # especially if/when the Interface tab is re-enabled.
            # For now, with Interface tab on hold, this might not be immediately necessary
            # unless other settings also strongly benefit from a restart.
            # Example:
            # if dialog.restart_required_flag: # Assuming dialog could set such a flag
            #     QMessageBox.information(self, "Settings Changed", 
            #                             "Some settings have been updated and may require an application restart to take full effect.")
        else:
            # "Cancel" was clicked or the dialog was closed otherwise.
            # No specific action needed here unless you want to log it internally.
            pass

    def open_about_dialog(self):
        about_dialog=AboutDialog(self)
        about_dialog.exec()

    def _apply_main_window_relevant_settings(self):
        """
        Applies settings from QSettings that are relevant to the main window's
        behavior or initial UI state, especially after SettingsDialog is used.
        """
        print("Applying main window relevant settings...")
        # 1. Default Download Path: Update placeholder or initial text if current is empty
        #    The _load_and_apply_settings_to_ui already handles initial load of last_download_path.
        #    This is more about reflecting the *new default* from settings if it changed.
        current_download_path = self.download_path_edit.text()
        default_dl_path_setting = self.settings.value(KEY_DEFAULT_DOWNLOAD_PATH, "", type=str)

        if not current_download_path and default_dl_path_setting:
            # If user cleared path, or on first proper load after setting default, fill it.
            self.download_path_edit.setText(default_dl_path_setting)
            print(f"Applied default download path from settings: {default_dl_path_setting}")
        elif not default_dl_path_setting and not self.download_path_edit.placeholderText():
             # If no default is set in settings, ensure placeholder reflects that
             self.download_path_edit.setPlaceholderText("Click 'Browse' or set a default in Settings...")


        # 2. Default Language and Quality: Update combo boxes if they should reflect new defaults
        #    Currently, main window loads "last_language/quality". If you want settings
        #    to override these as *new defaults* for the session:
        default_lang = self.settings.value(KEY_DEFAULT_LANGUAGE, self.lang_combo.currentText(), type=str)
        if self.lang_combo.findText(default_lang) != -1:
            # This might re-trigger save if signal blockers are not used here,
            # but this method is called *after* settings dialog.
            # For now, just ensuring the combo reflects the new default for next use.
            # To avoid triggering save, use QSignalBlocker if this is called frequently
            with QSignalBlocker(self.lang_combo):
                 if self.lang_combo.currentText() != default_lang: # Only set if different
                    self.lang_combo.setCurrentText(default_lang)
                    print(f"Updated language combo to default: {default_lang}")


        default_qual = self.settings.value(KEY_DEFAULT_QUALITY, self.quality_combo.currentText(), type=str)
        if self.quality_combo.findText(default_qual) != -1:
            with QSignalBlocker(self.quality_combo):
                if self.quality_combo.currentText() != default_qual: # Only set if different
                    self.quality_combo.setCurrentText(default_qual)
                    print(f"Updated quality combo to default: {default_qual}")


        # 3. FFmpeg Path for AnimeService (if AnimeService needs to be re-initialized or updated)
        #    Currently AnimeService checks on its own __init__. If FFmpeg path setting changes,
        #    AnimeService might need to be informed or re-created if its behavior depends on this path.
        #    For now, we assume AnimeService will use the path from QSettings when it needs FFmpeg,
        #    or yt-dlp will use the 'ffmpeg_location' option if set.
        #    The main window should pass the ffmpeg_location to anime_service.download_anime

        # 4. Download Retries for AnimeService
        #    This also needs to be passed to anime_service.download_anime method.
        
        print("Finished applying main window relevant settings.")

    def _connect_all_signals(self):
        """Connect signals from UI elements (setup by UiMainWindow) to methods in this class."""
        # Search
        self.search_input.returnPressed.connect(self.handle_search_action)
        self.search_btn.clicked.connect(self.handle_search_action)
        
        # Filter
        self.filter_input.textChanged.connect(self.handle_filter_table_text_changed)

        # Table
        self.search_results_table.cellClicked.connect(self.handle_table_row_selection)
        self.search_results_table.customContextMenuRequested.connect(self.handle_table_context_menu)
        self.search_results_table.cellDoubleClicked.connect(self.handle_table_row_double_click) # Example

        # Download Options
        self.lang_combo.currentTextChanged.connect(self.handle_language_change_for_episodes)
        self.lang_combo.currentTextChanged.connect(self.handle_setting_changed_and_save) # Save on change
        self.quality_combo.currentTextChanged.connect(self.handle_setting_changed_and_save)

        # Directory
        self.browse_path_btn.clicked.connect(self.handle_browse_directory_action)
        # If download_path_edit were editable:
        self.download_path_edit.textChanged.connect(self.handle_setting_changed_and_save)

        # Main Actions
        self.download_btn.clicked.connect(self.handle_download_action)
        self.toggle_log_btn.clicked.connect(self.handle_toggle_log_visibility)
        self.settings_btn.clicked.connect(self.open_settings_dialog)
        self.about_btn.clicked.connect(self.open_about_dialog)

        # Custom Thread Signals (from this class to its own slots)
        self.output_signal.connect(self.append_log_message)
        self.search_finished_signal.connect(self.handle_search_finished)
        self.update_episode_title_signal.connect(self.current_episode_title_label.setText)
        self.update_episode_progress_signal.connect(self.current_episode_progress_bar.setValue)
        self.update_batch_progress_signal.connect(self.handle_batch_progress_update)
        self.set_download_button_enabled_signal.connect(self.download_btn.setEnabled)

    def _restore_window_geometry(self):
        """
        Restores window size and position from settings.
        If restoration fails or no valid geometry is found, sets a default size.
        """
        geometry_data = self.settings.value("window_geometry")

        if not (geometry_data and isinstance(geometry_data, QByteArray) and not geometry_data.isEmpty() and self.restoreGeometry(geometry_data)):
            self.resize(1000, 600)

    def _save_window_geometry(self):
        """Saves current window size and position to settings."""
        # self.saveGeometry() returns a QByteArray.
        # If the window is not yet shown or in some very unusual state, it could be empty.
        # QSettings can store an empty QByteArray; upon loading, the isEmpty() check above would handle it.
        self.settings.setValue("window_geometry", self.saveGeometry())

    def _load_and_apply_settings_to_ui(self):
        """Load settings using QSettings and apply them to the relevant UI widgets,
           blocking signals to prevent premature saves."""
        
        # Language
        with QSignalBlocker(self.lang_combo): # Use direct access: self.lang_combo
            last_lang = self.settings.value("last_language", "SUB", type=str)
            if self.lang_combo.findText(last_lang, Qt.MatchFlag.MatchFixedString) != -1:
                self.lang_combo.setCurrentText(last_lang)

        # Quality
        with QSignalBlocker(self.quality_combo): # Use direct access: self.quality_combo
            last_quality = self.settings.value("last_quality", "1080p", type=str)
            if self.quality_combo.findText(last_quality, Qt.MatchFlag.MatchFixedString) != -1:
                self.quality_combo.setCurrentText(last_quality)

        # Download Path
        default_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
        app_folder_name = "HiAnime_Downloader_Downloads"
        if default_path:
            default_path = os.path.join(default_path, app_folder_name)
        else:
            doc_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
            if doc_path:
                default_path = os.path.join(doc_path, app_folder_name)
            else:
                default_path = os.path.join(os.path.expanduser("~"), app_folder_name)
        
        saved_path = self.settings.value("last_download_path", default_path, type=str)
        with QSignalBlocker(self.download_path_edit): # Use direct access: self.download_path_edit
            self.download_path_edit.setText(saved_path)

        # Log Visibility - NO QSignalBlocker needed here because setVisible and setText
        # for these specific widgets do not trigger the signals that call _save_settings.
        # The problem was that _save_settings was being called *before* this section ran,
        # due to signals from lang_combo etc.
        log_is_visible = self.settings.value("log_visible", True, type=bool)
        self._update_log_ui_state(log_is_visible) # Call the helper method

    def _save_settings(self):
        """Save current UI settings to QSettings."""
        self.settings.setValue("last_language", self.lang_combo.currentText())
        self.settings.setValue("last_quality", self.quality_combo.currentText())
        self.settings.setValue("last_download_path", self.download_path_edit.text())
        self.settings.setValue("log_visible", self.output_box.isVisible())
        self._save_window_geometry() # <--- Ensure this is called

    def _get_effective_ffmpeg_path(self) -> str | None:
        """
        Gets FFmpeg path from settings.
        Returns the stripped path if valid, or None if empty, whitespace-only, or not set.
        """
        # .value() will return "" if the key is missing (due to defaultValue="") or if value is ""
        ffmpeg_path_setting = self.settings.value(KEY_FFMPEG_PATH, "", type=str) 
        
        stripped_path = ffmpeg_path_setting.strip() # Remove leading/trailing whitespace
        
        # Return the stripped path only if it's not an empty string after stripping; otherwise, return None.
        return stripped_path if stripped_path else None 

    def _get_effective_download_retries(self) -> int:
        """Gets download retries from settings, default to 10."""
        return self.settings.value(KEY_DOWNLOAD_RETRIES, 10, type=int)

    def handle_setting_changed_and_save(self): # Generic slot for changed settings
        self._save_settings()

    def _apply_initial_ui_visibility_state(self):
        """Sets the initial visibility state for UI groups like download options."""
        self.update_download_options_visibility(False) # Hide download options group initially
        # Log visibility is handled by _load_and_apply_settings_to_ui

    def update_download_options_visibility(self, show: bool):
        """Controls visibility of download options and related progress bars."""
        # This list should match the widgets you intend to group for download operations
        elements_to_control = [
            self.lang_label, self.lang_combo,
            self.quality_label, self.quality_combo,
            self.start_label, self.start_spin,
            self.end_label, self.end_spin,
            self.download_btn, 
            self.current_episode_title_label, self.current_episode_progress_bar,
            self.batch_progress_label, self.batch_progress_bar
        ]
        for widget in elements_to_control:
            widget.setVisible(show)
        
        # Specific logic for download button: only show if options are shown AND an anime is selected
        if show and self.selected_anime_data:
            self.download_btn.show()
        else:
            self.download_btn.hide()
        
        # Progress bars only visible if a download is active
        if self.is_download_active and show:
            self.current_episode_title_label.show()
            self.current_episode_progress_bar.show()
            self.batch_progress_label.show()
            self.batch_progress_bar.show()
        elif not self.is_download_active : # Always hide if not downloading, even if options are shown
            self.current_episode_title_label.hide()
            self.current_episode_progress_bar.hide()
            self.batch_progress_label.hide()
            self.batch_progress_bar.hide()

    def append_log_message(self, text: str):
        # Use the helper function for stripping ANSI codes if text might contain them
        # cleaned_text = strip_ansi_codes(text) # from .helpers
        self.output_box.append(text) # Assume text is already clean or stripping happens earlier
        self.output_box.moveCursor(QTextCursor.MoveOperation.End)

    def handle_search_action(self): # Was search()
        anime_name = self.search_input.text().strip()
        if not anime_name:
            QMessageBox.warning(self, "Search Error", "Please enter an anime name.")
            return
        
        self.output_signal.emit(f"Searching for '{anime_name}'...")
        self.anime_results = [] 
        self.search_results_table.setRowCount(0) # Clear table
        self.selected_anime_data = None
        self.update_download_options_visibility(False) # Hide options

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.search_btn.setEnabled(False)
        self.search_input.setEnabled(False)
        
        # Run the search in a separate thread
        threading.Thread(target=self._execute_search_task, args=(anime_name,), daemon=True).start()

    def _execute_search_task(self, anime_name: str):
        """Worker thread method for searching anime."""
        try:
            # Call the AnimeService method
            self.anime_results = self.anime_service.search_anime(anime_name) 
        except Exception as e:
            # Log error through the service or directly if service doesn't log this high-level failure
            self.output_signal.emit(f"[ERROR] Search execution thread failed: {e}")
            self.anime_results = [] # Ensure results list is empty on error
        finally:
            self.search_finished_signal.emit() # Signal GUI thread that search is done

    def handle_search_finished(self): # Was _on_search_finished_slot()
        """Slot for search_finished_signal, runs in GUI thread."""
        QApplication.restoreOverrideCursor()
        self.search_btn.setEnabled(True)
        self.search_input.setEnabled(True)

        if self.anime_results:
            self.output_signal.emit(f"Found {len(self.anime_results)} result(s). Populating table...")
            self._populate_table_with_search_results() # Populate table with new results
        else:
            self.output_signal.emit("No results found or an error occurred during search.")
        # self.output_signal.emit("Search interface reactivated.") # Optional confirmation

    def _populate_table_with_search_results(self): # Was populate_search_results_table()
        """Populates the QTableWidget with anime search results."""
        self.search_results_table.setSortingEnabled(False)
        self.search_results_table.clearContents() # Clear existing content before new population
        self.search_results_table.setRowCount(len(self.anime_results))
        
        self.search_results_table.verticalHeader().setDefaultSectionSize(self.table_thumbnail_size.height() + 10)
        
        for row_idx, anime_data in enumerate(self.anime_results):
            # Column 0: Thumbnail
            img_url = anime_data.get("img")
            if img_url:
                cached_pixmap = self.pixmap_cache.find(img_url)
                if cached_pixmap and not cached_pixmap.isNull(): # Check if valid pixmap
                    self._set_image_widget_in_cell(row_idx, 0, cached_pixmap)
                else:
                    placeholder_item = QTableWidgetItem("...")
                    placeholder_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.search_results_table.setItem(row_idx, 0, placeholder_item)
                    self._request_image_load_for_cell(row_idx, 0, img_url)
            else:
                no_img_item = QTableWidgetItem("N/A")
                no_img_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.search_results_table.setItem(row_idx, 0, no_img_item)

            # Column 1: Title
            title_text = anime_data.get("title", "N/A")
            title_item = QTableWidgetItem(title_text)
            title_item.setData(Qt.ItemDataRole.UserRole, anime_data) # Store full dict
            tooltip_parts = [f"<b>{title_text}</b>"]
            if img_url and not (self.pixmap_cache.find(img_url) and not self.pixmap_cache.find(img_url).isNull()):
                tooltip_parts.append("<i>(Image loading...)</i>")
            title_item.setToolTip("\n".join(tooltip_parts))
            self.search_results_table.setItem(row_idx, 1, title_item)

            # Column 2: Sub Episodes
            sub_val = anime_data.get("sub", 0)
            sub_item = NumericTableWidgetItem() # From .helpers
            sub_item.setData(Qt.ItemDataRole.EditRole, sub_val) # Data for sorting
            sub_item.setText(str(sub_val))                     # Data for display
            sub_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.search_results_table.setItem(row_idx, 2, sub_item)

            # Column 3: Dub Episodes
            dub_val = anime_data.get("dub", 0)
            dub_item = NumericTableWidgetItem() # From .helpers
            dub_item.setData(Qt.ItemDataRole.EditRole, dub_val) # Data for sorting
            dub_item.setText(str(dub_val))                     # Data for display
            dub_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.search_results_table.setItem(row_idx, 3, dub_item)

        self.search_results_table.resizeColumnToContents(0) # Adjust thumbnail column
        # Other columns are either Stretch or Interactive, initial size from header label width
        self.search_results_table.setSortingEnabled(True)

    def _set_image_widget_in_cell(self, row: int, col: int, pixmap: QPixmap):
        """Creates a QLabel with the pixmap and sets it as the cell widget."""
        img_label = QLabel()
        img_label.setPixmap(pixmap) # Assumes pixmap is already scaled to self.table_thumbnail_size
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_label.setStyleSheet("background-color: transparent;") # Avoid QLabel default background
        self.search_results_table.setCellWidget(row, col, img_label)

    def _request_image_load_for_cell(self, row: int, col: int, image_url_str: str): # Was load_image_for_cell
        if not image_url_str: return
        url = QUrl(image_url_str)
        request = QNetworkRequest(url)
        reply = self.network_manager.get(request)
        self.active_image_requests[reply] = (row, col, image_url_str) # Track reply
        reply.finished.connect(self._handle_image_network_reply)

    def _handle_image_network_reply(self): # Was _on_image_reply_finished
        reply = self.sender() # Get the QNetworkReply object
        if not reply or reply not in self.active_image_requests:
            if reply: reply.deleteLater()
            return
        
        row, col, image_url = self.active_image_requests.pop(reply)
        placeholder_item = self.search_results_table.item(row, col) # If a placeholder QTableWidgetItem was set

        if reply.error() == QNetworkReply.NetworkError.NoError:
            image_data = reply.readAll()
            pixmap = QPixmap()
            if pixmap.loadFromData(image_data):
                # Scale pixmap before caching and displaying
                scaled_pixmap = pixmap.scaled(self.table_thumbnail_size, 
                                              Qt.AspectRatioMode.KeepAspectRatio, 
                                              Qt.TransformationMode.SmoothTransformation)
                self.pixmap_cache.insert(image_url, scaled_pixmap) # Cache the scaled version
                self._set_image_widget_in_cell(row, col, scaled_pixmap)
            else:
                if placeholder_item: placeholder_item.setText("Img Load Err")
                self.output_signal.emit(f"[ERROR] Could not load image data from {image_url}")
        else:
            if placeholder_item: placeholder_item.setText("Net Err")
            self.output_signal.emit(f"[ERROR] Network error for image {image_url}: {reply.errorString()}")
        reply.deleteLater() # Crucial to free network resources

    def handle_table_row_selection(self, row: int, column: int): # Was anime_selected_from_table
        # Data is stored in the UserRole of the Title item (column 1)
        title_item_for_data = self.search_results_table.item(row, 1) 
        if title_item_for_data and title_item_for_data.data(Qt.ItemDataRole.UserRole):
            self.selected_anime_data = title_item_for_data.data(Qt.ItemDataRole.UserRole)
            self.output_signal.emit(f"Selected: {self.selected_anime_data.get('title', 'N/A')}")
            self.update_download_options_visibility(True) # Show options now that item is selected
            self.handle_language_change_for_episodes() # Update episode range based on new selection
        else:
            self.selected_anime_data = None
            self.update_download_options_visibility(False)
            # self.output_signal.emit("[DEBUG] No data for selected table cell.") # Can be noisy

        # Hide progress elements that are not relevant until download starts
        if not self.is_download_active :
            self.current_episode_title_label.hide()
            self.current_episode_progress_bar.hide()
            self.batch_progress_label.hide()
            self.batch_progress_bar.hide()

    def handle_language_change_for_episodes(self, lang_text_unused=None): # Was update_episode_range_for_selected_anime
        if not self.selected_anime_data:
            self.start_spin.setEnabled(False); self.end_spin.setEnabled(False)
            return
        
        lang_key = self.lang_combo.currentText().lower() # "sub" or "dub"
        max_eps = self.selected_anime_data.get(lang_key, 0) # Get count for current lang

        if max_eps > 0:
            self.start_spin.setRange(1, max_eps); self.start_spin.setValue(1)
            self.end_spin.setRange(1, max_eps); self.end_spin.setValue(max_eps)
            self.start_spin.setEnabled(True); self.end_spin.setEnabled(True)
        else:
            # No episodes for this type, disable and reset spinners
            self.start_spin.setRange(1,1); self.start_spin.setValue(1); self.start_spin.setEnabled(False)
            self.end_spin.setRange(1,1); self.end_spin.setValue(1); self.end_spin.setEnabled(False)
            self.output_signal.emit(f"[INFO] No {lang_key.upper()} episodes for {self.selected_anime_data.get('title', 'N/A')}.")

    def handle_browse_directory_action(self): # Was select_download_directory
        current_path = self.download_path_edit.text()
        # Try to make the browse dialog open in a sensible location
        if not current_path or not os.path.isdir(current_path):
            current_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
            if not current_path: current_path = os.path.expanduser("~") # Fallback to home

        directory = QFileDialog.getExistingDirectory(self, "Select Download Directory", current_path)
        if directory: # If a directory was selected (dialog not cancelled)
            self.download_path_edit.setText(directory)
            self.output_signal.emit(f"Download directory set to: {directory}")
            self._save_settings() # Save setting immediately

    def handle_download_action(self): # Was download_selected_anime
        if not self.selected_anime_data:
            QMessageBox.warning(self, "Selection Error", "Please select an anime from the list first.")
            return
        
        download_dir = self.download_path_edit.text()
        if not (download_dir and os.path.isdir(os.path.abspath(download_dir))): # Validate directory
            QMessageBox.warning(self, "Directory Error", "Please select a valid download directory.")
            self.handle_browse_directory_action() # Call self.handle_browse_directory_action() here to re-prompt
            return

        title = self.selected_anime_data['title']
        url = self.selected_anime_data['url']
        lang = self.lang_combo.currentText() # "SUB" or "DUB" (service will lowercase)
        quality = self.quality_combo.currentText() # "1080p", etc.
        start_ep = self.start_spin.value()
        end_ep = self.end_spin.value()

        if self.selected_anime_data.get(lang.lower(), 0) == 0 or start_ep == 0 or end_ep == 0:
            QMessageBox.warning(self, "Episode Error", f"No {lang.upper()} episodes available or valid range selected for download.")
            return
        if start_ep > end_ep:
            QMessageBox.warning(self, "Range Error", "Start episode must be less than or equal to end episode.")
            return
        
        self.is_download_active = True
        self.total_episodes_in_batch = (end_ep - start_ep) + 1
        self.completed_episodes_in_batch = 0
        self.current_episode_last_pct = 0.0
        self.current_tracking_video_file = None # Reset for new batch

        self.update_download_options_visibility(True) # Ensure progress bars are visible
        self.current_episode_title_label.setText("Current file: Preparing download...")
        self.current_episode_progress_bar.setValue(0)
        self.batch_progress_bar.setRange(0, self.total_episodes_in_batch)
        self.batch_progress_bar.setValue(0)
        self.batch_progress_bar.setFormat(f"%v of {self.total_episodes_in_batch} episodes (%p%)")
        self.batch_progress_label.setText(f"Overall batch: 0 of {self.total_episodes_in_batch} processed")
        
        self.set_download_button_enabled_signal.emit(False) # Disable download button
        self.output_signal.emit(
            f"Starting download for '{title}' (Episodes {start_ep}-{end_ep}, {lang}, {quality}) to '{download_dir}'"
        )

        threading.Thread(target=self._execute_download_task, 
                         args=(title, url, lang, quality, start_ep, end_ep, download_dir), 
                         daemon=True).start()

    def _execute_download_task(self, title, url, lang, quality, start_ep, end_ep, base_download_dir):
        """Worker thread method for downloading anime."""
        ffmpeg_location = self._get_effective_ffmpeg_path()
        download_retries = self._get_effective_download_retries()
        
        self.current_operation_details = (
            f"Downloading: {title} (Ep {start_ep}-{end_ep}, {lang}, {quality})\n"
            f"To: {base_download_dir}\n"
            f"FFmpeg: {'Auto-detect' if not ffmpeg_location else ffmpeg_location}\n" # Display FFmpeg info
            f"Retries: {download_retries}"
        )

        try:
            self.anime_service.download_anime( # Call the AnimeService method
                title, url, lang, quality, start_ep, end_ep, base_download_dir,
                gui_logger_callback=self.output_signal.emit, # For yt-dlp's internal logger
                progress_hook_for_gui=self._download_progress_hook,
                postprocessor_hook_for_gui=self._postprocessor_hook,
                log_ytdlp_debug_to_gui=False,
                ffmpeg_location=ffmpeg_location, # <-- PASS FFMPEG PATH
                download_retries=download_retries,
            )
            
        except Exception as e:
            self.output_signal.emit(f"[CRITICAL ERROR] Download thread for '{title}' encountered an error: {e}")
            # import traceback
            # self.output_signal.emit(f"Traceback: {traceback.format_exc()}")
        finally:
            self.is_download_active = False # Mark download as inactive
            self.set_download_button_enabled_signal.emit(True) # Re-enable download button
            
            # Emit a final status message for the current episode title area
            final_status_msg = "Batch processing concluded."
            if self.total_episodes_in_batch > 0: # If a batch was actually defined
                if self.completed_episodes_in_batch == self.total_episodes_in_batch:
                    final_status_msg = f"Batch completed: All {self.total_episodes_in_batch} episodes processed."
                    if self.total_episodes_in_batch == 1: # If only one episode, ensure its bar is 100%
                         self.update_episode_progress_signal.emit(100)
                else: # Partial completion or errors
                    final_status_msg = (
                        f"Batch ended: {self.completed_episodes_in_batch} of {self.total_episodes_in_batch} "
                        f"episodes processed. Check log for details."
                    )
            self.update_episode_title_signal.emit(final_status_msg)
            # Batch progress bar should already reflect the final state from hooks.

    def _download_progress_hook(self, d):
        """Callback hook from yt-dlp for download progress. Runs in download thread."""
        status = d.get('status')
        filename_from_hook = d.get('filename', '')
        # Use strip_ansi_codes from .helpers
        cleaned_filename = strip_ansi_codes(filename_from_hook) 
        base_filename_current_op = os.path.basename(cleaned_filename) if cleaned_filename else "N/A"
        is_current_op_video = any(cleaned_filename.lower().endswith(ext) for ext in self.video_extensions)

        if status == 'downloading':
            percent_str_for_log = strip_ansi_codes(d.get('_percent_str', '0.0%').strip())
            speed_str_for_log = strip_ansi_codes(d.get('_speed_str', 'N/A').strip())
            speed_str_for_log = speed_str_for_log.strip()
            eta_str_for_log = strip_ansi_codes(d.get('_eta_str', 'N/A').strip())
            
            # Optional: log detailed download progress for non-video files too
            if is_current_op_video and base_filename_current_op == self.current_tracking_video_file:
                self.output_signal.emit(
                    f"DL '{base_filename_current_op}': {percent_str_for_log} @ {speed_str_for_log} (ETA: {eta_str_for_log}s)"
                )

            if is_current_op_video:
                if self.current_tracking_video_file != base_filename_current_op: # New video file started
                    self.current_tracking_video_file = base_filename_current_op
                    self.current_episode_last_pct = 0.0
                    self.update_episode_progress_signal.emit(0) # Reset individual bar
                    
                    info_dict = d.get('info_dict', {})
                    ep_num_str = str(info_dict.get('episode_number', ''))
                    ep_title_str = strip_ansi_codes(str(info_dict.get('episode', info_dict.get('title', ''))))
                    if not ep_title_str or ep_title_str == "N/A": ep_title_str = base_filename_current_op
                    
                    display_title = f"Episode {ep_num_str} - {ep_title_str}" if ep_num_str else ep_title_str
                    self.update_episode_title_signal.emit(f"Downloading: {display_title}")
                
                try: # Update progress bar for current video
                    current_pct_float = float(percent_str_for_log.replace('%', ''))
                    if current_pct_float >= self.current_episode_last_pct: # Ensure progress moves forward
                        self.current_episode_last_pct = current_pct_float
                        self.update_episode_progress_signal.emit(int(current_pct_float))
                except ValueError: pass # Ignore if percent string cannot be converted

        elif status == 'finished':
            self.output_signal.emit(f"Finished component: {base_filename_current_op}")
            if is_current_op_video and base_filename_current_op == self.current_tracking_video_file:
                self.update_episode_progress_signal.emit(100) # Mark current video as 100%
                self.completed_episodes_in_batch += 1
                # Emit signal to update batch progress UI
                self.update_batch_progress_signal.emit(self.completed_episodes_in_batch, self.total_episodes_in_batch)
                self.output_signal.emit(f"--- Video Episode '{base_filename_current_op}' fully processed. ---")
                self.current_tracking_video_file = None # Reset for next video in batch
                self.current_episode_last_pct = 0.0

    def _postprocessor_hook(self, d):
        """Callback hook from yt-dlp for postprocessing. Runs in download thread."""
        status = d.get('status')
        pp_name = d.get('postprocessor')
        info_dict = d.get('info_dict', {}) # Contains 'filepath' for final output
        final_filepath = info_dict.get('filepath', 'UnknownFile')
        base_filename = os.path.basename(final_filepath)

        if status == 'started':
            self.output_signal.emit(f"Post-processing '{base_filename}' with [{pp_name}]...")
            if pp_name == 'FixupM3u8':  # Assuming FixupM3u8 is reliably the first
                self.update_episode_title_signal.emit(f"Post-processing: {base_filename}...")
        elif status == 'finished':
            self.output_signal.emit(f"Post-processing '{base_filename}' with [{pp_name}] finished.")
            if pp_name == 'MoveFiles':  # Assuming MoveFiles is reliably the last
                self.update_episode_title_signal.emit(f"Processed: {base_filename}")
        elif status == 'error':
            error_details = d.get('msg', 'Unknown postprocessing error')
            self.output_signal.emit(f"[ERROR] Post-processing '{base_filename}' [{pp_name}] failed: {error_details}")

    def handle_batch_progress_update(self, completed_count: int, total_in_batch: int): # Was _update_batch_ui_slot
        """Updates the batch progress UI elements."""
        self.batch_progress_bar.setValue(completed_count)
        self.batch_progress_label.setText(f"Overall batch: {completed_count} of {total_in_batch} processed")
        
        # If batch is not yet complete, prepare UI for the next episode
        if completed_count < total_in_batch and self.is_download_active: # Check is_download_active
            self.update_episode_title_signal.emit("Current file: Awaiting next episode...")
            self.update_episode_progress_signal.emit(0) # Reset individual progress bar

    def _update_log_ui_state(self, is_visible: bool):
        """Updates the output log's visibility and the toggle button's text."""
        self.output_box.setVisible(is_visible)
        self.toggle_log_btn.setText("Hide Output Log" if is_visible else "Show Output Log")

    def handle_toggle_log_visibility(self): # Was toggle_output_log_visibility
        is_visible = not self.output_box.isVisible()
        self.output_box.setVisible(is_visible)
        self._update_log_ui_state(is_visible)    # Call the helper method to update UI
        self._save_settings() # Save this preference

    def handle_filter_table_text_changed(self, text: str): # Was filter_search_table
        filter_text = text.lower().strip()
        for row_num in range(self.search_results_table.rowCount()):
            title_item = self.search_results_table.item(row_num, 1) # Title is in column 1
            if title_item:
                # Hide row if filter_text is not empty AND title doesn't contain filter_text
                should_hide = bool(filter_text) and (filter_text not in title_item.text().lower())
                self.search_results_table.setRowHidden(row_num, should_hide)
            else: # Should not happen if table is populated correctly
                self.search_results_table.setRowHidden(row_num, bool(filter_text))

    def handle_table_context_menu(self, position): # Was show_table_context_menu
        selected_indexes = self.search_results_table.selectedIndexes()
        if not selected_indexes: return

        selected_row = selected_indexes[0].row() # Get row from first selected index
        title_item = self.search_results_table.item(selected_row, 1) # Title item from column 1
        
        if not (title_item and title_item.data(Qt.ItemDataRole.UserRole)): return
        
        anime_data_for_menu = title_item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)

        copy_title_action = QAction(f"Copy Title: {anime_data_for_menu.get('title', 'N/A')}", self)
        copy_title_action.triggered.connect(lambda: QApplication.clipboard().setText(anime_data_for_menu.get('title', '')))
        menu.addAction(copy_title_action)

        if anime_data_for_menu.get('url'):
            view_online_action = QAction("View on HiAnime", self)
            view_online_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl(anime_data_for_menu.get('url'))))
            menu.addAction(view_online_action)
        
        menu.exec(self.search_results_table.viewport().mapToGlobal(position))

    def handle_table_row_double_click(self, row: int, column: int): # Was handle_table_double_click
        # Default action: select the row (as if single-clicked)
        self.handle_table_row_selection(row, column)
        # Optional: could also immediately trigger download or open details, etc.

    def closeEvent(self, event):
        """Handles the window close event."""
        self._save_settings() # Always save settings on close attempt
        if self.is_download_active:
            reply = QMessageBox.question(
                self, 'Confirm Exit',
                "Downloads are in progress. Are you sure you want to exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No # Default to No
            )
            if reply == QMessageBox.StandardButton.Yes:
                # Add any necessary cleanup for active threads if possible (hard with daemon threads)
                event.accept()
            else:
                event.ignore()
        else:
            event.accept() # No active downloads, close normally
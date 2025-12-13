from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QTextEdit, QPushButton, QTableWidget, QComboBox, 
                             QSpinBox, QSpacerItem, QSizePolicy, QProgressBar, 
                             QHeaderView) # Ensure all used widgets are imported
from PyQt6.QtGui import QFont
from PyQt6.QtCore import QSize, Qt, QCoreApplication # Added QCoreApplication

class UiMainWindow(object):
    def setupUi(self, MainWindow_instance): # MainWindow_instance is your AnimeDownloaderWindow
        MainWindow_instance.setObjectName("AnimeDownloaderWindow")
        MainWindow_instance.main_layout = QVBoxLayout(MainWindow_instance) # Apply layout directly to the passed window

        # --- Search Area ---
        search_hbox = QHBoxLayout()
        MainWindow_instance.search_input = QComboBox() # Changed to QComboBox for search history
        MainWindow_instance.search_input.setEditable(True)
        # Placeholder text will be set in retranslateUi
        search_hbox.addWidget(MainWindow_instance.search_input)
        MainWindow_instance.search_btn = QPushButton() # Text set in retranslateUi
        search_hbox.addWidget(MainWindow_instance.search_btn)
        MainWindow_instance.main_layout.addLayout(search_hbox)

        # --- Filter Input ---
        filter_hbox = QHBoxLayout()
        MainWindow_instance.filter_label = QLabel() # Text set in retranslateUi
        filter_hbox.addWidget(MainWindow_instance.filter_label)
        MainWindow_instance.filter_input = QLineEdit()
        # Placeholder text will be set in retranslateUi
        MainWindow_instance.filter_input.setClearButtonEnabled(True)
        filter_hbox.addWidget(MainWindow_instance.filter_input)
        MainWindow_instance.main_layout.addLayout(filter_hbox)

        # --- Results Table ---
        MainWindow_instance.search_results_table = QTableWidget()
        # MainWindow_instance.table_thumbnail_size is an attribute set by the controller (AnimeDownloaderWindow)
        if hasattr(MainWindow_instance, 'table_thumbnail_size'):
             MainWindow_instance.search_results_table.setIconSize(MainWindow_instance.table_thumbnail_size)
        else: # Fallback
             MainWindow_instance.search_results_table.setIconSize(QSize(80,120)) # Example default
        
        MainWindow_instance.search_results_table.setColumnCount(4)
        # Header labels set in retranslateUi or controller if dynamic
        MainWindow_instance.search_results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        MainWindow_instance.search_results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        MainWindow_instance.search_results_table.setAlternatingRowColors(True)
        MainWindow_instance.search_results_table.setSortingEnabled(True)
        MainWindow_instance.search_results_table.verticalHeader().setVisible(False)
        MainWindow_instance.search_results_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        header = MainWindow_instance.search_results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # Thumbnail
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)         # Title
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)     # Sub
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)     # Dub
        MainWindow_instance.main_layout.addWidget(MainWindow_instance.search_results_table)

        # --- Download Options Group ---
        MainWindow_instance.lang_label = QLabel() # Text set in retranslateUi
        MainWindow_instance.lang_combo = QComboBox()
        MainWindow_instance.lang_combo.addItems(["SUB", "DUB"]) # These are values, not for translation usually
        
        MainWindow_instance.quality_label = QLabel() # Text set in retranslateUi
        MainWindow_instance.quality_combo = QComboBox()
        MainWindow_instance.quality_combo.addItems(["1080p", "720p", "360p"]) # Values

        options_lang_quality_layout = QHBoxLayout()
        options_lang_quality_layout.addWidget(MainWindow_instance.lang_label)
        options_lang_quality_layout.addWidget(MainWindow_instance.lang_combo)
        options_lang_quality_layout.addWidget(MainWindow_instance.quality_label)
        options_lang_quality_layout.addWidget(MainWindow_instance.quality_combo)
        options_lang_quality_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        MainWindow_instance.main_layout.addLayout(options_lang_quality_layout)

        MainWindow_instance.start_label = QLabel() # Text set in retranslateUi
        MainWindow_instance.start_spin = QSpinBox()
        MainWindow_instance.start_spin.setRange(1,1); MainWindow_instance.start_spin.setValue(1)
        
        MainWindow_instance.end_label = QLabel() # Text set in retranslateUi
        MainWindow_instance.end_spin = QSpinBox()
        MainWindow_instance.end_spin.setRange(1,1); MainWindow_instance.end_spin.setValue(1)

        options_episode_layout = QHBoxLayout()
        options_episode_layout.addWidget(MainWindow_instance.start_label)
        options_episode_layout.addWidget(MainWindow_instance.start_spin)
        options_episode_layout.addWidget(MainWindow_instance.end_label)
        options_episode_layout.addWidget(MainWindow_instance.end_spin)
        options_episode_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        MainWindow_instance.main_layout.addLayout(options_episode_layout)

        # --- Download Directory ---
        dir_selection_layout = QHBoxLayout()
        MainWindow_instance.download_dir_label = QLabel() # Text set in retranslateUi
        dir_selection_layout.addWidget(MainWindow_instance.download_dir_label)
        MainWindow_instance.download_path_edit = QLineEdit()
        # Placeholder text set in retranslateUi
        MainWindow_instance.download_path_edit.setReadOnly(False)
        dir_selection_layout.addWidget(MainWindow_instance.download_path_edit, 1) # Stretch
        MainWindow_instance.browse_path_btn = QPushButton() # Text set in retranslateUi
        dir_selection_layout.addWidget(MainWindow_instance.browse_path_btn)
        MainWindow_instance.view_folder_btn = QPushButton() # Text set in retranslateUi
        dir_selection_layout.addWidget(MainWindow_instance.view_folder_btn)
        MainWindow_instance.main_layout.addLayout(dir_selection_layout)

        # --- Progress Area ---
        MainWindow_instance.current_episode_title_label = QLabel() # Text set by controller
        MainWindow_instance.main_layout.addWidget(MainWindow_instance.current_episode_title_label)
        MainWindow_instance.current_episode_progress_bar = QProgressBar()
        MainWindow_instance.current_episode_progress_bar.setValue(0)
        MainWindow_instance.current_episode_progress_bar.setTextVisible(True)
        MainWindow_instance.current_episode_progress_bar.setFormat("%p%")

        MainWindow_instance.main_layout.addWidget(MainWindow_instance.current_episode_progress_bar)

        MainWindow_instance.batch_progress_label = QLabel() # Text set by controller
        MainWindow_instance.main_layout.addWidget(MainWindow_instance.batch_progress_label)
        MainWindow_instance.batch_progress_bar = QProgressBar()
        MainWindow_instance.batch_progress_bar.setValue(0)
        MainWindow_instance.batch_progress_bar.setTextVisible(True)

        MainWindow_instance.main_layout.addWidget(MainWindow_instance.batch_progress_bar)

        # --- Action Buttons ---
        action_buttons_layout = QHBoxLayout() # Create a new layout for these buttons
        MainWindow_instance.download_btn = QPushButton()
        action_buttons_layout.addWidget(MainWindow_instance.download_btn) # Add to new HBox
        MainWindow_instance.toggle_log_btn = QPushButton()
        action_buttons_layout.addWidget(MainWindow_instance.toggle_log_btn) # Add to new HBox
        # *** ADD SETTINGS BUTTON HERE ***
        MainWindow_instance.settings_btn = QPushButton()
        action_buttons_layout.addWidget(MainWindow_instance.settings_btn) # Add to new HBox
        MainWindow_instance.about_btn = QPushButton()
        action_buttons_layout.addWidget(MainWindow_instance.about_btn) # Add to new HBox
        # *** END OF ADDITION ***
        action_buttons_layout.addStretch() # Add a spacer to push buttons to one side if desired
        MainWindow_instance.main_layout.addLayout(action_buttons_layout) # Add this HBox to main_layout


        # --- Output Log ---
        MainWindow_instance.output_box = QTextEdit()
        MainWindow_instance.output_box.setReadOnly(True)
        MainWindow_instance.output_box.setFont(QFont("consolas", 10))
        MainWindow_instance.output_box.setStyleSheet("background-color: #2B2B2B; color: #A9B7C6; border: 1px solid #444;")
        MainWindow_instance.main_layout.addWidget(MainWindow_instance.output_box)

        self.retranslateUi(MainWindow_instance)

    def retranslateUi(self, MainWindow_instance):
        _translate = QCoreApplication.translate
        MainWindow_instance.setWindowTitle(_translate("AnimeDownloaderWindow", "HiAnime Downloader"))
        
        # Search Area
        MainWindow_instance.search_input.setPlaceholderText(_translate("AnimeDownloaderWindow", "Enter anime name or select from download history..."))
        MainWindow_instance.search_btn.setText(_translate("AnimeDownloaderWindow", "Search"))

        # Filter Input
        MainWindow_instance.filter_label.setText(_translate("AnimeDownloaderWindow", "Filter:"))
        MainWindow_instance.filter_input.setPlaceholderText(_translate("AnimeDownloaderWindow", "Filter results by title..."))

        # Results Table Headers
        MainWindow_instance.search_results_table.setHorizontalHeaderLabels([
            _translate("AnimeDownloaderWindow", "Thumbnail"),
            _translate("AnimeDownloaderWindow", "Title  "), # Extra spaces for sort arrow
            _translate("AnimeDownloaderWindow", "Sub Eps  "),
            _translate("AnimeDownloaderWindow", "Dub Eps  ")
        ])
        
        # Download Options
        MainWindow_instance.lang_label.setText(_translate("AnimeDownloaderWindow", "Language:"))
        MainWindow_instance.quality_label.setText(_translate("AnimeDownloaderWindow", "Quality:"))
        MainWindow_instance.start_label.setText(_translate("AnimeDownloaderWindow", "Start Ep:"))
        MainWindow_instance.end_label.setText(_translate("AnimeDownloaderWindow", "End Ep:"))
        
        # Download Directory
        MainWindow_instance.download_dir_label.setText(_translate("AnimeDownloaderWindow", "Download Directory:"))
        MainWindow_instance.download_path_edit.setPlaceholderText(_translate("AnimeDownloaderWindow", "Click 'Browse' to select..."))
        MainWindow_instance.browse_path_btn.setText(_translate("AnimeDownloaderWindow", "Browse..."))
        MainWindow_instance.view_folder_btn.setText(_translate("AnimeDownloaderWindow", "View Folder"))

        # Progress Area (initial static text if any - mostly dynamic)
        MainWindow_instance.current_episode_title_label.setText(_translate("AnimeDownloaderWindow", "Current file: N/A"))
        MainWindow_instance.batch_progress_label.setText(_translate("AnimeDownloaderWindow", "Overall batch: N/A"))

        # Action Buttons
        MainWindow_instance.download_btn.setText(_translate("AnimeDownloaderWindow", "Download Selected Anime"))
        MainWindow_instance.settings_btn.setText(_translate("AnimeDownloaderWindow", "Settings"))
        MainWindow_instance.about_btn.setText(_translate("AnimeDownloaderWindow", "About"))
        # *** END OF ADDITION ***
        # toggle_log_btn text is set dynamically by controller based on state
        # MainWindow_instance.toggle_log_btn.setText(_translate("AnimeDownloaderWindow", "Hide Output Log"))
import os
import sys
import requests
import pip_system_certs
import re
import shutil
import time
from PyQt6.QtCore import QObject, pyqtSignal
from yt_dlp import YoutubeDL
from yt_dlp.utils import clean_html, get_element_by_class, get_elements_html_by_class
from yt_dlp_plugins.extractor import hianime

DEFAULT_BASE_URL = "https://hianime.to" # Update if needed, or make configurable
VERSION_REGEX = re.compile(r'^__version__\s*=\s*["\'](?P<version>[^"\']+)["\']', re.M)

class Logger:
    """
    Handles logging for both console and GUI.  yt-dlp uses this class for its
    'logger' option.
    """
    def __init__(self, gui_callback_fn=None, context_name="Service"):
        """
        Initializes the logger.

        Args:
            gui_callback_fn:  A callable (e.g., a Qt signal's emit method) that accepts a string.
                            If provided, log messages will be sent to the GUI via this callback.
            context_name:   A string describing the source of the log messages
                            (e.g., "AnimeService", "yt-dlp", "PluginLoader").  This is used to
                            prefix console log messages for clarity.
        """
        self.gui_callback_fn = gui_callback_fn
        self.context_name = context_name
        # By default, do NOT send raw debug messages to the GUI.
        self.log_debug_to_gui = False

    def _console_log(self, level_str, msg):
        """
        Helper to consistently format and print log messages to the console.
        """
        # Handle Unicode encoding issues on Windows
        try:
            print(f"[{self.context_name} {level_str.upper()}] {msg}",
                  file=sys.stderr if level_str.upper() in ["ERROR", "WARNING"] else sys.stdout)
        except UnicodeEncodeError:
            # Replace problematic characters
            safe_msg = msg.encode('utf-8', 'replace').decode('utf-8')
            print(f"[{self.context_name} {level_str.upper()}] {safe_msg}",
                  file=sys.stderr if level_str.upper() in ["ERROR", "WARNING"] else sys.stdout)

    def debug(self, msg):
        """
        Handles debug-level log messages.  These are typically very verbose
        and are usually only useful for developers.

        Args:
            msg: The log message string.
        """
        self._console_log("debug", msg)  # Always print debug to console
        if self.log_debug_to_gui and self.gui_callback_fn:
            #  If explicitly enabled, send to GUI (might be verbose).  Consider
            #  prefixing or filtering these, as yt-dlp's debug output can be quite noisy.
            self.gui_callback_fn(f"[{self.context_name} DEBUG] {msg}")

    def info(self, msg):
        """
        Handles info-level log messages.  These are general informational
        messages about the operation of the program.

        Args:
            msg: The log message string.
        """
        self._console_log("info", msg)
        if self.gui_callback_fn:
            # For info messages, send them to the GUI callback.  yt-dlp often sends
            # messages that are directly usable in the GUI.  Internal service logs
            #  are also usually fine as-is.
            self.gui_callback_fn(msg)

    def warning(self, msg):
        """
        Handles warning-level log messages.  These indicate potential problems
        or unexpected situations that do not prevent the program from continuing.

        Args:
            msg: The log message string.
        """
        # Ensure [WARNING] prefix for GUI messages if not already present
        gui_msg = msg if msg.lstrip().upper().startswith("[WARNING]") else f"[WARNING] {msg}"
        self._console_log("warning", msg)  # Console gets context prefix
        if self.gui_callback_fn:
            self.gui_callback_fn(gui_msg)

    def error(self, msg):
        """
        Handles error-level log messages.  These indicate that a serious
        problem has occurred and some operation has failed.

        Args:
            msg: The log message string.
        """
        # Ensure [ERROR] prefix for GUI messages if not already present
        gui_msg = msg if msg.lstrip().upper().startswith("[ERROR]") else f"[ERROR] {msg}"
        self._console_log("error", msg)  # Console gets context prefix
        if self.gui_callback_fn:
            self.gui_callback_fn(gui_msg)

class AnimeService(QObject):
    download_completed_signal = pyqtSignal(str)  # Emits the anime title when download completes

    def __init__(self, base_url=None):
        super().__init__()
        self.base_url = base_url if base_url else DEFAULT_BASE_URL
        self._service_logger = Logger()

        self.ffmpeg_path = self._find_ffmpeg()

        if self.ffmpeg_path:
            self._service_logger.info(f"FFmpeg found at: {self.ffmpeg_path}")
        else:
            self._service_logger.warning(
                "FFmpeg not found in system PATH. Some features like embedding subtitles or "
                "format conversions require FFmpeg. If yt-dlp cannot locate it, "
                "these operations may fail."
            )
        # If you were to implement automatic downloading, you might call a method here
        # to check/download FFmpeg to a specific app directory and set self.ffmpeg_path
        # or a specific path for yt-dlp's 'ffmpeg_location' option.

    def _find_ffmpeg(self) -> str | None:
        """
        Tries to find FFmpeg in the system PATH.
        Returns the path to FFmpeg if found, otherwise None.
        """
        return shutil.which("ffmpeg")

    def is_ffmpeg_available(self) -> bool:
        """
        Checks if FFmpeg was found by the service's initial check in the PATH.
        Note: yt-dlp might still find FFmpeg in other locations.
        """
        return bool(self.ffmpeg_path)

    def set_gui_logger_callback(self, gui_callback_fn, log_debug_to_gui=False):
        """Allows the GUI to set a callback for the service's internal logger."""
        self._service_logger.gui_callback_fn = gui_callback_fn
        self._service_logger.log_debug_to_gui = log_debug_to_gui

    def search_anime(self, name: str) -> list:
        # Using hianimez.to from your original downloader.py. Adapt base_url if needed.
        # For consistency, use self.base_url if this search is also for hianime.to
        # If search uses a different domain, define it explicitly.
        search_base_url = self.base_url
        search_url = f"{search_base_url}/search?keyword={name}"
        self._service_logger.info(f"Searching for anime: {name} on {search_url}")
        results = []

        try:
            response = requests.get(search_url, headers={"Referer": search_base_url}, timeout=10)
            response.raise_for_status()
            webpage = response.text
        except requests.RequestException as e:
            self._service_logger.error(f"Error downloading search page: {e}")
            return []

        # Adapt your existing parsing logic from downloader.py's search_anime here
        # Ensure clean_html, get_element_by_class, get_elements_html_by_class are imported
        anime_elements = get_elements_html_by_class('flw-item', webpage)
        if not anime_elements:
            self._service_logger.warning(f"No anime elements found on search page for '{name}'. Site structure might have changed.")
            return []

        for element_html in anime_elements:
            title = clean_html(get_element_by_class('film-name', element_html))
            url_match = re.search(r'href="(/watch/[^"]+)"', element_html)

            if not (title and url_match):
                self._service_logger.warning(f"Skipped item: missing title or URL. Title found: '{title}'")
                continue

            anime_path = url_match.group(1)
            anime_full_url = f"{search_base_url}{anime_path}" # Use search_base_url

            sub, dub = 0, 0
            try:
                sub_text = get_element_by_class('tick-item tick-sub', element_html)
                if sub_text: sub = int(clean_html(sub_text))
            except (ValueError, TypeError): self._service_logger.warning(f"Could not parse sub count for {title}.")
            try:
                dub_text = get_element_by_class('tick-item tick-dub', element_html)
                if dub_text: dub = int(clean_html(dub_text))
            except (ValueError, TypeError): self._service_logger.warning(f"Could not parse dub count for {title}.")

            img_url = None
            img_match = re.search(r'data-src="([^"]+)"', element_html)
            if img_match: img_url = img_match.group(1)

            results.append({"title": title, "url": anime_full_url, "sub": sub, "dub": dub, "img": img_url})

        self._service_logger.info(f"Search for '{name}' found {len(results)} results.")
        return results

    def sanitize_filename_component(self, name: str) -> str: # Renamed from sanitize_directory_name for clarity
        """Sanitizes a string to be used as a valid file or directory name component."""
        if not isinstance(name, str): name = str(name)
        name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
        name = name.strip(' ._')
        return name if name else "untitled"

    def download_anime(self, title, url, lang, quality, start_ep, end_ep,base_download_dir,
                       gui_logger_callback=None,  # For yt-dlp's logger
                       progress_hook_for_gui=None,
                       postprocessor_hook_for_gui=None,
                       log_ytdlp_debug_to_gui=False,
                       ffmpeg_location: str | None = None,  # From settings
                       download_retries: int = 10):         # From settings
        """
        Downloads anime episodes using yt-dlp, with logging to console and optional GUI.

        Args:
            title: The title of the anime series.
            url: The URL of the anime episode or playlist.
            lang: The language (e.g., "SUB", "DUB").
            quality: The desired video quality (e.g., "1080p", "720p").
            start_ep: The starting episode number.
            end_ep: The ending episode number.
            base_download_dir: The base directory where downloads should be stored.
            gui_logger_callback: A callable (e.g., a Qt signal's emit method) to send log
                messages to the GUI.  If None, logs are only printed to the console.
            progress_hook_for_gui:  A hook function for yt-dlp to report download progress
                to the GUI.
            postprocessor_hook_for_gui: A hook for post-processing steps.
            log_ytdlp_debug_to_gui:  If True, yt-dlp's DEBUG messages are also sent to
                the GUI via gui_logger_callback.  Default is False to avoid flooding
                the GUI with verbose output.
            ffmpeg_location: Explicit path to FFmpeg executable from settings. Defaults to None.
            download_retries: Number of times to retry a download. Defaults to 10.
        """
        
        ytdlp_logger = Logger(gui_logger_callback, context_name="yt-dlp")
        ytdlp_logger.log_debug_to_gui = True  # Enable debug messages to GUI
        ytdlp_logger.log_debug_to_gui = log_ytdlp_debug_to_gui

        if not hianime:
            ytdlp_logger.error("HiAnime IE class not loaded. Cannot download.")
            return
        '''
        try:
            plugin_ie_key = hianime.ie_key()
            if not plugin_ie_key or not isinstance(plugin_ie_key, str):
                raise ValueError(f"Invalid ie_key ('{plugin_ie_key}') from plugin.")
        except Exception as e:
            ytdlp_logger.error(f"Could not get/validate ie_key from HiAnime plugin: {e}")
            return
        '''
        sanitized_series_title = self.sanitize_filename_component(title)

        try:
            os.makedirs(base_download_dir, exist_ok=True)
        except OSError as e:
            ytdlp_logger.error(f"Failed to ensure base download directory '{base_download_dir}': {e}")
            return

        series_dir = os.path.join(base_download_dir, sanitized_series_title)
        try:
            os.makedirs(series_dir, exist_ok=True)
        except OSError as e:
            ytdlp_logger.error(f"Failed to create series download directory '{series_dir}': {e}")
            return

        output_template = os.path.join(series_dir, '%(series)s - Episode %(episode_number)s - %(episode)s.%(ext)s')
        qualities = ['1080p', '720p', '480p', '360p', '240p', '144p']
        selected_quality = quality.lower()
        if selected_quality in qualities:
            index = qualities.index(selected_quality)
            fallback_qualities = qualities[index:] + ['best']
            plugin_custom_format = '/'.join(fallback_qualities)
        else:
            plugin_custom_format = 'best'

        opts = {
            "playliststart": start_ep,
            "playlistend": end_ep,
            "format": plugin_custom_format,
            "outtmpl": output_template,
            "postprocessors": [{'key': 'FFmpegEmbedSubtitle'},
                             {'key': 'FFmpegMetadata', 'add_metadata': True, 'add_infojson': 'if_exists'}],
            "subtitleslangs": ["all"], # Consider making this configurable if needed
            "writesubtitles": True,
            "writeautomaticsub": True, # Consider making this configurable
            "progress_hooks": [progress_hook_for_gui] if progress_hook_for_gui else [],
            "postprocessor_hooks": [postprocessor_hook_for_gui] if postprocessor_hook_for_gui else [],
            "logger": ytdlp_logger,
            "quiet": True,
            "no_warnings": False,
            "verbose": False,
            "ignoreerrors": False,
            "continuedl": True, # Consider making this configurable
            "retries": download_retries,             # Using parameter from settings
            "fragment_retries": download_retries,    # Using parameter from settings
            "ffmpeg_location": ffmpeg_location,   # Using parameter from settings (already None or valid path)
            "nocheckcertificate": True,  # Bypass SSL certificate verification to handle SSL issues
            "http_headers": {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
            }
        }

        # --- FFmpeg Path and Warning Logic ---
        # The ffmpeg_location parameter is guaranteed by main_window.py to be either
        # a non-empty stripped path string or None.
        # No need for: "if not ffmpeg_location: opts['ffmpeg_location'] = None" as ffmpeg_location is already correct.

        if opts.get('ffmpeg_location'):
            # A specific path for FFmpeg is provided via settings.
            ytdlp_logger.info(f"Using FFmpeg path from settings: {opts['ffmpeg_location']}")
        elif not self.is_ffmpeg_available(): # Checks initial PATH scan by AnimeService
            # No explicit FFmpeg path set in settings, AND AnimeService's initial PATH check failed.
            ytdlp_logger.warning(
                "FFmpeg-dependent post-processing is enabled. FFmpeg was not found in system PATH "
                "by initial check, and no specific path is configured in settings. "
                "Processing may fail if yt-dlp cannot auto-detect FFmpeg."
            )
        # else: No explicit path from settings, but self.is_ffmpeg_available() was True (found in PATH).
        # yt-dlp will try to find it in PATH. No warning needed from our app here.

        ytdlp_logger.info(
            f"Preparing download: {title} (Ep {start_ep}-{end_ep}, {lang}, {quality}) to {series_dir}\n"
            f"Using plugin: HiAnime, format: '{plugin_custom_format}', URL: {url}\n"
            f"FFmpeg path for this operation: {'Auto-detect by yt-dlp' if not opts.get('ffmpeg_location') else opts.get('ffmpeg_location')}"
        )

        # Add lang to url
        url = f"{url}&lang={lang.lower()}" if '?' in url else f"{url}?lang={lang.lower()}"

        qualities = ['1080p', '720p', '480p', '360p', '240p', '144p']
        selected_quality = quality.lower()
        plugin_custom_format = selected_quality

        max_retries = 10
        for attempt in range(max_retries):
            try:
                with YoutubeDL(opts) as ydl:
                    ydl.extract_info(url, download=True)
                ytdlp_logger.info(f"Download process for {title} (yt-dlp phase) finished.")
                self.download_completed_signal.emit(title)  # Emit signal for download history
                break  # Success, exit loop
            except Exception as e:
                error_msg = str(e)
                if "Requested format is not available" in error_msg:
                    if attempt < max_retries - 1:
                        ytdlp_logger.warning(f"Attempt {attempt + 1} failed: Selected quality '{selected_quality}' not available. Retrying in 10 seconds...")
                        time.sleep(10)
                        continue
                    else:
                        # After 10 attempts, fallback
                        ytdlp_logger.warning(f"Selected quality '{selected_quality}' not available after {max_retries} attempts, trying fallback qualities.")
                        if selected_quality in qualities:
                            index = qualities.index(selected_quality)
                            fallback_qualities = qualities[index + 1:] + ['best']  # Skip the selected, start from next
                            fallback_format = '/'.join(fallback_qualities)
                            opts['format'] = fallback_format
                            ytdlp_logger.info(f"Retrying with fallback format: {fallback_format}")
                            with YoutubeDL(opts) as ydl:
                                ydl.extract_info(url, download=True)
                            ytdlp_logger.info(f"Download process for {title} (yt-dlp phase) finished with fallback.")
                            self.download_completed_signal.emit(title)
                        else:
                            raise
                else:
                    # For other errors, fail immediately
                    raise 

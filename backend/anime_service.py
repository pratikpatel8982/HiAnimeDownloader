import os
import sys
import importlib.util
import requests
import re
import shutil
import tempfile
from packaging.version import Version as PkgVersion, InvalidVersion # Import InvalidVersion to handle potential errors

from yt_dlp import YoutubeDL
from yt_dlp.utils import clean_html, get_element_by_class, get_elements_html_by_class

# --- Constants for Plugin Management ---
# Correctly determine PLUGIN_DIR relative to this file (anime_service.py)
_SERVICE_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_DIR = os.path.join(_SERVICE_FILE_DIR, "plugins") # plugins/ is a subdir of backend/
HIANIME_PLUGIN_FILENAME = "hianime.py"
PLUGIN_PATH = os.path.join(PLUGIN_DIR, HIANIME_PLUGIN_FILENAME)
PLUGIN_URL = "https://raw.githubusercontent.com/pratikpatel8982/yt-dlp-hianime/master/yt_dlp_plugins/extractor/hianime.py"

HIANIME_IE_CLASS_NAME_PRIMARY = "HiAnimeIE"

DEFAULT_BASE_URL = "https://hianimez.to" # Update if needed, or make configurable
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
        # The progress_hook is usually better for curated GUI progress.
        self.log_debug_to_gui = False

    def _console_log(self, level_str, msg):
        """
        Helper to consistently format and print log messages to the console.
        """
        # Use a consistent format for console output, including the context name.
        print(f"[{self.context_name} {level_str.upper()}] {msg}",
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

class AnimeService:
    def __init__(self, base_url=None):
        self.base_url = base_url if base_url else DEFAULT_BASE_URL
        self.hianime_ie_class = None  # Cache the loaded IE class
        self._service_logger = Logger() # Internal logger, not for GUI callbacks by default
        self._ensure_hianime_extractor()

        self.ffmpeg_path = self._find_ffmpeg() # <--- Check for FFmpeg on init

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

    def _ensure_hianime_extractor(self, check_existence_only=False):
        """
        Ensures the HiAnime extractor plugin is loaded if it exists.
        If check_existence_only is True, it only checks if the file exists
        without attempting download or loading.
        """
        if self.hianime_ie_class:
            return True # Already loaded

        if not os.path.exists(PLUGIN_PATH):
            self._service_logger.debug(f"Plugin file not found at {PLUGIN_PATH}.")
            return False # Plugin file doesn't exist

        if check_existence_only:
            self._service_logger.debug(f"Plugin file found at {PLUGIN_PATH} during existence check.")
            return True # File exists

        # Proceed with loading the plugin if it exists and check_existence_only is False
        try:
            spec_name = f"yt_dlp_plugins.extractor.{HIANIME_PLUGIN_FILENAME[:-3]}" # e.g., yt_dlp_plugins.extractor.hianime

            spec = importlib.util.spec_from_file_location(spec_name, PLUGIN_PATH)
            if spec is None or spec.loader is None:
                self._service_logger.error(f"Failed to create spec for HiAnime extractor from {PLUGIN_PATH}")
                return False

            hianime_module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = hianime_module # Important: Register module
            spec.loader.exec_module(hianime_module)

            if hasattr(hianime_module, HIANIME_IE_CLASS_NAME_PRIMARY):
                self.hianime_ie_class = getattr(hianime_module, HIANIME_IE_CLASS_NAME_PRIMARY)
            else:
                self._service_logger.error(f"Could not find class '{HIANIME_IE_CLASS_NAME_PRIMARY}' in {PLUGIN_PATH}")
                del sys.modules[spec.name] # Unregister if class not found
                return False

            self._service_logger.info(f"HiAnime extractor '{self.hianime_ie_class.__name__}' loaded from {PLUGIN_PATH}.")
            return True
        except Exception as e:
            self._service_logger.error(f"Failed to load HiAnime extractor plugin from {PLUGIN_PATH}: {e}")
            # Optional: attempt to remove corrupted plugin
            # if os.path.exists(PLUGIN_PATH):
            #     try: os.remove(PLUGIN_PATH); self._logger.info(f"Removed potentially corrupt plugin: {PLUGIN_PATH}")
            #     except OSError as oe: self._logger.error(f"Error removing plugin {PLUGIN_PATH}: {oe}")
            return False

    def _get_plugin_version(self, filepath: str) -> str | None:
        """
        Reads the __version__ string from a Python file.
        Returns the version string or None if not found or file doesn't exist/is unreadable.
        """
        if not os.path.exists(filepath):
            self._service_logger.debug(f"File not found to get version: {filepath}")
            return None
        try:
            # Read the beginning of the file to find the version string efficiently
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                # Read up to a reasonable size (e.g., 4KB) or fewer lines
                # Reading a fixed number of bytes is often faster than reading lines
                # for large files, but for a small plugin, reading lines is fine.
                # Let's read a max number of lines as version is usually at the top.
                content_head = ""
                for _ in range(20): # Read max 20 lines
                    line = f.readline()
                    if not line: break # End of file
                    content_head += line

                match = VERSION_REGEX.search(content_head)
                if match:
                    return match.group('version')
        except Exception as e:
            # Catch potential errors during file reading
            self._service_logger.error(f"Failed to read version from {filepath}: {e}")
            return None
        self._service_logger.debug(f"__version__ string not found in the first 20 lines of {filepath}.")
        return None # Version string not found in the first lines

    def check_plugin_version(self) -> tuple[str, str | None, str | None]:
        """
        Checks if a newer version of the HiAnime extractor plugin is available
        by comparing __version__ strings using the packaging library.

        Returns a tuple:
        (status: str - "update_available", "up_to_date", "local_newer", "error", "plugin_missing", "remote_version_unavailable")
        local_version: str | None
        remote_version: str | None)
        """
        self._service_logger.info(f"Checking for plugin updates from {PLUGIN_URL}...")
        local_version_str = self._get_plugin_version(PLUGIN_PATH)
        remote_version_str = None

        if local_version_str is None and not os.path.exists(PLUGIN_PATH):
            # Plugin file doesn't exist locally at all
            self._service_logger.info("Local plugin file not found.")

        try:
            # Fetch the remote file content to extract its version
            response = requests.get(PLUGIN_URL, timeout=10)
            response.raise_for_status()
            remote_content = response.text

            # Use a temporary file to extract the remote version safely
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.py', delete=False, encoding='utf-8') as tmp_file:
                tmp_file.write(remote_content)
                tmp_file_path = tmp_file.name

            remote_version_str = self._get_plugin_version(tmp_file_path)

            # Clean up the temporary file
            os.remove(tmp_file_path)

        except requests.RequestException as e:
            self._service_logger.error(f"Error fetching remote plugin for version check: {e}")
            return "error", local_version_str, None
        except Exception as e:
            self._service_logger.error(f"Unexpected error during remote version extraction: {e}")
            return "error", local_version_str, None

        if local_version_str is None:
            if remote_version_str is None:
                # Local missing, Remote version not found
                return "plugin_missing", None, None # More specific status
            else:
                # Local missing, Remote version found
                return "update_available", None, remote_version_str
        else: # Local plugin exists
            if remote_version_str is None:
                # Local exists, Remote version not found
                return "remote_version_unavailable", local_version_str, None
            else:
                # Both local and remote versions found, compare them using packaging
                try:
                    local_ver = PkgVersion(local_version_str)
                    remote_ver = PkgVersion(remote_version_str)

                    if remote_ver > local_ver:
                        return "update_available", local_version_str, remote_version_str
                    elif remote_ver < local_ver:
                        return "local_newer", local_version_str, remote_version_str
                    else: # remote_ver == local_ver
                        return "up_to_date", local_version_str, remote_version_str
                except InvalidVersion as e:
                    self._service_logger.error(f"Invalid version string encountered during comparison: {e}")
                    return "error", local_version_str, remote_version_str # Indicate error if versions are invalid


    def download_plugin(self) -> tuple[bool, str, str | None]:
        """
        Downloads the latest version of the HiAnime extractor plugin
        and replaces the local file safely.

        Returns a tuple:
        (success: bool,
        status_message: str,
        downloaded_version: str | None)
        """
        os.makedirs(PLUGIN_DIR, exist_ok=True)
        self._service_logger.info(f"Attempting to download HiAnime extractor plugin from: {PLUGIN_URL}")

        temp_file_path = None
        downloaded_version = None
        try:
            # Download to a temporary file
            with requests.get(PLUGIN_URL, stream=True, timeout=15) as r:
                r.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
                # Use tempfile.NamedTemporaryFile for robust temporary file handling
                with tempfile.NamedTemporaryFile(mode='wb', dir=PLUGIN_DIR, delete=False) as tmp_file:
                    temp_file_path = tmp_file.name
                    for chunk in r.iter_content(chunk_size=8192):
                        tmp_file.write(chunk)

            # Validate the downloaded file
            # Check if it's not empty and contains the __version__ string
            if os.path.getsize(temp_file_path) == 0:
                self._service_logger.error("Downloaded plugin file is empty.")
                return False, "Downloaded file is empty.", None

            downloaded_version = self._get_plugin_version(temp_file_path)
            if downloaded_version is None:
                self._service_logger.error("Downloaded plugin file does not appear valid (missing __version__).")
                return False, "Downloaded file validation failed (missing __version__).", None

            # Replace the old plugin file with the new one atomically if possible
            os.replace(temp_file_path, PLUGIN_PATH)

            # Invalidate the cached IE class so it's reloaded next time
            self.hianime_ie_class = None
            # Also remove from sys.modules if it was loaded
            spec_name = f"yt_dlp_plugins.extractor.{HIANIME_PLUGIN_FILENAME[:-3]}"
            if spec_name in sys.modules:
                del sys.modules[spec_name]

            self._service_logger.info(f"HiAnime extractor plugin downloaded and updated successfully to version {downloaded_version}.")
            return True, f"Plugin updated successfully to version {downloaded_version}.", downloaded_version

        except requests.RequestException as e:
            self._service_logger.error(f"Error downloading HiAnime extractor plugin: {e}")
            return False, f"Error downloading plugin: {e}", None
        except Exception as e:
            self._service_logger.error(f"Unexpected error during plugin download: {e}")
            return False, f"An unexpected error occurred during download: {e}", None
        finally:
            # Clean up the temporary file if it still exists (e.g., on error before replace)
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except OSError as e:
                    # Log a warning if cleanup fails, but don't block the main process
                    self._service_logger.warning(f"Failed to remove temporary file {temp_file_path}: {e}")

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

    def download_anime(self, title, url, lang, quality, start_ep, end_ep,
                       base_download_dir,
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
        ytdlp_logger.log_debug_to_gui = log_ytdlp_debug_to_gui

        if not self.hianime_ie_class:
            ytdlp_logger.error("HiAnime IE class not loaded. Cannot download.")
            return

        try:
            plugin_ie_key = self.hianime_ie_class.ie_key()
            if not plugin_ie_key or not isinstance(plugin_ie_key, str):
                raise ValueError(f"Invalid ie_key ('{plugin_ie_key}') from plugin.")
        except Exception as e:
            ytdlp_logger.error(f"Could not get/validate ie_key from HiAnime plugin: {e}")
            return

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
        plugin_custom_format = f"{lang.lower()}_{quality.lower()}"

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
            "ffmpeg_location": ffmpeg_location   # Using parameter from settings (already None or valid path)
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

        try:
            with YoutubeDL(opts) as ydl:
                ydl.add_info_extractor(self.hianime_ie_class())
                ydl.extract_info(url, download=True, ie_key=plugin_ie_key)
            ytdlp_logger.info(f"Download process for {title} (yt-dlp phase) finished.")
        except Exception as e:
            ytdlp_logger.error(f"Download of '{title}' failed: {type(e).__name__} - {e}")
            # import traceback
            # ytdlp_logger.debug(f"Traceback: {traceback.format_exc()}") 

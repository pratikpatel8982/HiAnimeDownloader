## HiAnimeDownloader

A GUI application to search and download anime from HiAnime.

This project is a desktop application designed to make it easy to find and download your favorite anime from the HiAnime website. It features a simple graphical user interface to search for titles, browse episodes, and manage downloads.

### Key Features
* **Search Functionality:** Find anime by title directly from the application.
* **GUI Interface:** User-friendly interface built with PyQt6.
* **Dependency Management:** Seamlessly handles external download libraries like yt-dlp.
* **Customizable Downloads:** Specify resolution and language for your downloads.

***

### Installation

You can set up and run this project using either **Poetry** (recommended) or a standard **`requirements.txt`** file.

#### Option 1: Using Poetry (Recommended)

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/pratikpatel8982/HiAnimeDownloader.git](https://github.com/pratikpatel8982/HiAnimeDownloader.git)
    cd HiAnimeDownloader
    ```

2.  **Install dependencies:**
    This command will read the `pyproject.toml` file and install all necessary packages.
    ```bash
    poetry install
    ```

3.  **Run the application:**
    ```bash
    poetry run python main.pyw
    ```

#### Option 2: Using `requirements.txt`

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/pratikpatel8982/HiAnimeDownloader.git](https://github.com/pratikpatel8982/HiAnimeDownloader.git)
    cd HiAnimeDownloader
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    ```

3.  **Activate the virtual environment:**
    * On Windows: `venv\Scripts\activate`
    * On macOS/Linux: `source venv/bin/activate`

4.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Run the application:**
    ```bash
    python main.pyw
    ```

***

### Building an Executable

You can package this application into a single executable file for easy distribution using **PyInstaller**. The process is slightly different depending on your installation method.

#### Using Poetry

1.  **Install PyInstaller:**
    ```bash
    poetry run pip install pyinstaller
    ```
2.  **Build the executable:**
    ```bash
    poetry run pyinstaller --onefile --name HiAnimeDownloader main.pyw
    ```

#### Using `requirements.txt`

1.  **Activate your virtual environment.**
2.  **Install PyInstaller:**
    ```bash
    pip install pyinstaller
    ```
3.  **Build the executable:**
    ```bash
    pyinstaller --onefile --windowed --name HiAnimeDownloader main.py
    ```

The final executable will be located in the `dist` folder.

***

### Dependencies
* `requests`
* `pip-system-certs`
* `yt-dlp`
* `pyqt6`
* `yt-dlp-hianime`

***

### License

This project is licensed under the MIT License. See the `LICENSE` file for details.
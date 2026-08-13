# Multi-Threaded 16K Video Downloader--

A powerful, asynchronous desktop application built with Python and PyQt6 that leverages `yt-dlp` to download high-definition videos (up to 16K) from various streaming platforms. It features concurrent downloading, custom row UI elements, and built-in anonymity support via Tor proxy routing.

## 🚀 Features

- **High-Resolution Support:** Downloads upto 16K media by automatically stitching video and audio streams.
- **Multi-Threaded Performance:** Runs downloads on background `QThread` workers to keep the user interface smooth and responsive.
- **Anonymity Toggle:** Route your traffic through a local Tor proxy with a single click to bypass IP throttling or geo-blocks.
- **Clean UI:** Clean desktop interface built with PyQt6, featuring download progress bars and silent background processes (no flashing command prompts on Windows).

## 📋 Prerequisites

Before running the application, ensure you have the following system dependencies installed:

1. **Python 3.7+**
2. **FFmpeg:** Crucial for merging separate high-quality video and audio streams. 
   - *Windows:* Install via `scoop install ffmpeg` or download from the official site and add it to your System `PATH`.
   - *macOS:* Install via Homebrew: `brew install ffmpeg`
   - *Linux:* Install via APT: `sudo apt install ffmpeg`
3. **Tor Service (Optional):** Required only if you plan to use the Tor Proxy feature. Ensure the Tor background service is running on its default port (`9050`).

## ⚙️ Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/aasimdott/YT-DLP-GUI.git
   cd YT-DLP-GUI
   ```

2. **Install Python dependencies:**
   ```bash
   pip install PyQt6 yt-dlp
   ```
   ```bash
   pip install -U "yt-dlp[default]" curl_cffi
   ```
3. **Install ffmpeg**
## 💻 Usage

1. Open your terminal in the project directory.
2. Launch the application:
   ```bash
   python Script.py
   ```
3. Paste your desired video URL, configure your download directory, toggle Tor if needed, and click **Download**.

## Tor (Optional)
- In localhost on port :9050

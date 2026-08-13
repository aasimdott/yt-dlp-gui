import sys
import os
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QComboBox, QFileDialog, QListWidget,
    QProgressBar, QLabel, QCheckBox, QListWidgetItem
)
from PyQt6.QtCore import QThread, pyqtSignal, QObject, Qt


# Helper to find bundled executable assets at runtime
def get_asset_path(binary_name):
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = ""

    full_name = f"{binary_name}.exe" if not binary_name.endswith(".exe") else binary_name
    target_path = os.path.join(base_path, full_name)

    return target_path if os.path.exists(target_path) else binary_name


class DownloadWorker(QObject):
    progress = pyqtSignal(float, str)  # percentage, status text
    finished = pyqtSignal(bool)        # success status

    def __init__(self, url, resolution, save_dir, use_tor, is_mp3):
        super().__init__()
        self.url = url
        self.resolution = resolution
        self.save_dir = save_dir
        self.use_tor = use_tor
        self.is_mp3 = is_mp3
        self._is_killed = False
        self.process = None

    def run(self):
        ytdlp_path = get_asset_path("yt-dlp")
        ffmpeg_dir = getattr(sys, '_MEIPASS', '') if getattr(sys, 'frozen', False) else None

        cmd = [ytdlp_path, "-P", self.save_dir, "--newline", "--continue"]

        # Configure commands based on format type (MP3 vs Video Resolutions)
        if self.is_mp3:
            cmd.extend([
                "-x",
                "--audio-format", "mp3",
                "--audio-quality", "0"  # Best quality VBR
            ])
        else:
            res_map = {
                "16K (2160p)": "bestvideo[height<=8640]+bestaudio/best",
                "8K (4320p)": "bestvideo[height<=4320]+bestaudio/best",
                "4K (2160p)": "bestvideo[height<=2160]+bestaudio/best",
                "2K (1140p)": "bestvideo[height<=1140]+bestaudio/best",
                "1080p": "bestvideo[height<=1080]+bestaudio/best",
                "720p": "bestvideo[height<=720]+bestaudio/best",
                "480p": "bestvideo[height<=480]+bestaudio/best",
                "Best Quality": "bestvideo+bestaudio/best"
            }
            fmt = res_map.get(self.resolution, "best")
            cmd.extend(["-f", fmt, "--merge-output-format", "mp4"])

        if ffmpeg_dir:
            cmd.extend(["--ffmpeg-location", ffmpeg_dir])

        if self.use_tor:
            cmd.extend(["--proxy", "socks5://127.0.0.1:9050"])

        cmd.append(self.url)

        try:
            startupinfo = None
            if os.name == 'nt' or sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                startupinfo=startupinfo
            )

            for line in self.process.stdout:
                if self._is_killed:
                    break

                line = line.strip()
                if "[download]" in line and "%" in line:
                    try:
                        parts = line.split()
                        pct_str = [p for p in parts if "%" in p][0].replace("%", "")
                        pct = float(pct_str)

                        speed = "Downloading..."
                        if "at" in parts:
                            speed_idx = parts.index("at") + 1
                            if speed_idx < len(parts):
                                speed = f"{parts[speed_idx]}"

                        self.progress.emit(pct, speed)
                    except Exception:
                        pass
                elif "[Merger]" in line or "[ExtractAudio]" in line:
                    self.progress.emit(99.0, "Processing audio/video...")

            self.process.wait()

            if self._is_killed:
                self.finished.emit(False)
            else:
                self.progress.emit(100.0, "Finished")
                self.finished.emit(True)

        except Exception as e:
            self.progress.emit(0.0, f"Error: {str(e)}")
            self.finished.emit(False)

    def terminate_download(self):
        self._is_killed = True
        if self.process:
            self.process.terminate()
            self.process.kill()  # Force kill if terminate doesn't work


class QueueItemWidget(QWidget):
    status_changed = pyqtSignal()  # Signal to inform the main interface to check the queue sequential automation

    def __init__(self, url, parent_gui):
        super().__init__()
        self.url = url
        self.parent_gui = parent_gui
        self.save_dir = os.path.expanduser("~")

        self.thread = None
        self.worker = None
        self.is_running = False
        self.is_done = False
        self.is_paused = False

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)

        # Row 1: URL Meta Information Label
        short_url = self.url[:60] + "..." if len(self.url) > 60 else self.url
        self.info_label = QLabel(f"🔗 {short_url}")
        self.info_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.info_label)

        # Row 2: Per-Item Custom Configuration Options Bar
        config_layout = QHBoxLayout()

        # Quality Format Selector Configuration
        self.format_combo = QComboBox()
        self.format_combo.addItems([
            "Best Quality", "4K (2160p)", "2K (1140p)", "1080p", "720p", "480p", "Audio MP3"
        ])
        config_layout.addWidget(QLabel("Format:"))
        config_layout.addWidget(self.format_combo)

        # Output Folder Selection Configuration
        self.folder_btn = QPushButton("📁 Folder")
        self.folder_btn.setFixedWidth(85)
        self.folder_btn.clicked.connect(self.select_row_folder)
        self.folder_label = QLabel(self.save_dir)
        self.folder_label.setStyleSheet("color: gray;")
        config_layout.addWidget(self.folder_btn)
        config_layout.addWidget(self.folder_label, 1)

        # Local Security Isolation Configuration
        self.tor_checkbox = QCheckBox("Tor Proxy")
        config_layout.addWidget(self.tor_checkbox)

        layout.addLayout(config_layout)

        # Row 3: Live Progress, Tracking Metrics & Dynamic Controls
        action_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.status_label = QLabel("Idle")
        self.status_label.setFixedWidth(110)

        self.action_btn = QPushButton("Start")
        self.action_btn.setFixedWidth(75)
        self.action_btn.clicked.connect(self.toggle_download)

        action_layout.addWidget(self.progress_bar)
        action_layout.addWidget(self.status_label)
        action_layout.addWidget(self.action_btn)
        layout.addLayout(action_layout)

        # Divider frame visual aesthetic boundary accentuation
        line = QWidget()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #ddd; margin-top: 5px;")
        layout.addWidget(line)

        self.setLayout(layout)

    def select_row_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Save Directory", self.save_dir)
        if folder:
            self.save_dir = folder
            self.folder_label.setText(folder)

    def start_download(self):
        """Manually start the download"""
        if not self.is_running and not self.is_done:
            self.toggle_download()

    def toggle_download(self):
        if not self.is_running:
            # Start download
            self.is_running = True
            self.is_paused = False
            self.action_btn.setText("Pause")
            self.status_label.setText("Connecting...")

            # Freeze configuration controls during the execution phase
            self.format_combo.setEnabled(False)
            self.folder_btn.setEnabled(False)
            self.tor_checkbox.setEnabled(False)

            selected_format = self.format_combo.currentText()
            is_mp3 = (selected_format == "Audio MP3")

            self.thread = QThread()
            self.worker = DownloadWorker(
                self.url, selected_format, self.save_dir,
                self.tor_checkbox.isChecked(), is_mp3
            )
            self.worker.moveToThread(self.thread)

            self.thread.started.connect(self.worker.run)
            self.worker.progress.connect(self.update_row_progress)
            self.worker.finished.connect(self.handle_row_finished)

            self.thread.start()
            self.status_changed.emit()
        else:
            # Pause download
            self.status_label.setText("Stopping...")
            self.cleanup_worker()
            self.is_running = False
            self.is_paused = True
            self.status_label.setText("Paused")
            self.action_btn.setText("Resume")

            # Unlock configuration options upon suspension
            self.format_combo.setEnabled(True)
            self.folder_btn.setEnabled(True)
            self.tor_checkbox.setEnabled(True)
            self.status_changed.emit()

    def update_row_progress(self, percent, speed_text):
        self.progress_bar.setValue(int(percent))
        self.status_label.setText(speed_text)

    def handle_row_finished(self, success):
        self.cleanup_worker()
        self.is_running = False

        if success:
            self.is_done = True
            self.status_label.setText("Finished")
            self.action_btn.setText("Done")
            self.action_btn.setEnabled(False)
        else:
            if not self.is_paused:
                self.status_label.setText("Failed")
                self.action_btn.setText("Retry")
                self.format_combo.setEnabled(True)
                self.folder_btn.setEnabled(True)
                self.tor_checkbox.setEnabled(True)
            else:
                # If it was paused, keep it as paused
                self.is_paused = False

        self.status_changed.emit()

    def cleanup_worker(self):
        self.is_running = False
        if self.worker:
            self.worker.terminate_download()
        if self.thread:
            self.thread.quit()
            self.thread.wait()
        self.worker = None
        self.thread = None


class YtdlpGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Universal Download Module")
        self.setMinimumSize(800, 550)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Simple URL Insertion Interface Box
        url_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste link here and click add...")
        self.add_btn = QPushButton("Add to Download Queue")
        self.add_btn.clicked.connect(self.add_to_queue)
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.add_btn)
        main_layout.addLayout(url_layout)

        # Multi-Item List Component Execution Area
        main_layout.addWidget(QLabel("Active Jobs Queue:"))
        self.queue_widget = QListWidget()
        # Set selection mode to none to focus interactions on row elements smoothly
        self.queue_widget.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        main_layout.addWidget(self.queue_widget)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def add_to_queue(self):
        url = self.url_input.text().strip()
        if not url:
            return

        list_item = QListWidgetItem(self.queue_widget)
        row_widget = QueueItemWidget(url, self)
        list_item.setSizeHint(row_widget.sizeHint())
        self.queue_widget.addItem(list_item)
        self.queue_widget.setItemWidget(list_item, row_widget)
        self.url_input.clear()

        # Auto-start removed - user must manually click "Start" for each download


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = YtdlpGUI()
    window.show()
    sys.exit(app.exec())

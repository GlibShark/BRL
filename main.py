import sys
import json
import requests
import zipfile
import io
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QComboBox, QPushButton, QTextEdit, QLabel, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import subprocess

class DownloadThread(QThread):
    update_progress = pyqtSignal(int)
    update_log = pyqtSignal(str)

    def __init__(self, url, category, version):
        super().__init__()
        self.url = url
        self.category = category
        self.version = version

    def run(self):
        try:
            self.update_log.emit(f"Starting download: {self.url}")
            response = requests.get(self.url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            
            zip_content = bytearray()
            progress = 0
            for data in response.iter_content(chunk_size=1024):
                zip_content.extend(data)
                progress += len(data)
                self.update_progress.emit(int((progress / total_size) * 100))
            
            self.update_log.emit("Extracting files...")
            install_dir = os.path.join("games", self.category, self.version)
            os.makedirs(install_dir, exist_ok=True)
            with zipfile.ZipFile(io.BytesIO(zip_content)) as zip_ref:
                zip_ref.extractall(install_dir)
            
            self.update_log.emit("Installation completed successfully!")
            
        except Exception as e:
            self.update_log.emit(f"Error: {str(e)}")

class LauncherWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Buckshot Roulette Launcher (BRL)")
        self.setGeometry(100, 100, 600, 400)
        
        self.central_widget = QWidget()
        self.layout = QVBoxLayout()
        
        self.category_label = QLabel("Select platform:")
        self.category_combo = QComboBox()
        
        self.version_label = QLabel("Select version:")
        self.version_combo = QComboBox()
        
        self.progress = QProgressBar()
        self.log_output = QTextEdit()
        self.play_btn = QPushButton("Play")
        self.warning_label = QLabel("")

        self.layout.addWidget(self.category_label)
        self.layout.addWidget(self.category_combo)
        self.layout.addWidget(self.version_label)
        self.layout.addWidget(self.version_combo)
        self.layout.addWidget(self.progress)
        self.layout.addWidget(self.log_output)
        self.layout.addWidget(self.warning_label)  
        self.layout.addWidget(self.play_btn)
        
        self.central_widget.setLayout(self.layout)
        self.setCentralWidget(self.central_widget)
        
        self.versions = {}
        self.current_category = ""
        
        self.play_btn.clicked.connect(self.start_play)
        self.category_combo.currentTextChanged.connect(self.update_versions)
        self.version_combo.currentTextChanged.connect(self.check_version_warning)  
        
        self.load_versions()

    def log(self, message):
        self.log_output.append(message)

    def load_versions(self):
        try:
            response = requests.get("https://cdn.sharknet.fun/br/list.json")
            self.versions = json.loads(response.text)
            
            self.category_combo.clear()
            self.category_combo.addItems(self.versions.keys())
            
            self.log("Successfully loaded version list")
        except Exception as e:
            self.log(f"Error loading versions: {str(e)}")

    def update_versions(self, category):
        self.current_category = category.lower()
        self.version_combo.clear()
        self.version_combo.addItems(self.versions.get(category, []))
        
        self.warning_label.setText("")

    def check_version_warning(self):
        category = self.category_combo.currentText().lower()
        version = self.version_combo.currentText()
        
        # Show warning immediately when version is selected
        if category == "itchio" and version == "1.2.2":
            self.warning_label.setText("Warning: Unofficial build. Only OpenGL supported.")
            self.warning_label.setStyleSheet("color: red;")
        else:
            self.warning_label.setText("")

    def start_play(self):
        category = self.category_combo.currentText().lower()
        version = self.version_combo.currentText()
        
        if not category or not version:
            self.log("Please select both platform and version")
            return
        
        install_dir = os.path.join("games", category, version)
        
        if not os.path.exists(install_dir):
            self.log(f"Game not found, starting download...")
            url = f"https://cdn.sharknet.fun/br/ver/{category}/{version}.zip"
            
            self.download_thread = DownloadThread(url, category, version)
            self.download_thread.update_progress.connect(self.progress.setValue)
            self.download_thread.update_log.connect(self.log)
            self.download_thread.start()
        else:
            self.log(f"Launching game from: {install_dir}")
            game_executable = os.path.join(install_dir, "game.exe")
            if os.path.exists(game_executable):
                subprocess.Popen(game_executable)
            else:
                self.log("Error: Game executable not found.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LauncherWindow()
    window.show()
    sys.exit(app.exec())

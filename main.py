import sys
import os
import threading
import time
import requests
import pyperclip
from flask import Flask, request, send_from_directory
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QTextEdit, QFileDialog, QMessageBox, QLabel
)
from PyQt5.QtCore import Qt

# --- CONFIG ---
PEER_URL = "http://localhost:5000"  # Change to peer IP
SHARED_FOLDER = "./shared"             # Folder to store received files

# --- Flask Server ---
app = Flask(__name__)

@app.route("/clipboard", methods=["GET", "POST"])
def clipboard_api():
    if request.method == "POST":
        pyperclip.copy(request.json.get("text", ""))
        return {"status": "ok"}
    return {"clipboard": pyperclip.paste()}

@app.route("/upload", methods=["POST"])
def upload_file():
    f = request.files['file']
    f.save(os.path.join(SHARED_FOLDER, f.filename))
    return {"status": "uploaded"}

@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(SHARED_FOLDER, filename)

def run_server():
    app.run(port=5000, host="0.0.0.0")

# --- Clipboard Poller ---
def clipboard_sync():
    last_text = ""
    while True:
        try:
            current_text = pyperclip.paste()
            if current_text != last_text:
                requests.post(f"{PEER_URL}/clipboard", json={"text": current_text})
                last_text = current_text
        except Exception:
            pass
        time.sleep(2)

# --- Qt5 GUI App ---
class ClipboardApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Clipboard & File Share")
        self.setMinimumSize(400, 300)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.clipboard_label = QLabel("Clipboard Content:")
        layout.addWidget(self.clipboard_label)

        self.clipboard_text = QTextEdit()
        self.clipboard_text.setReadOnly(True)
        layout.addWidget(self.clipboard_text)

        self.get_clipboard_btn = QPushButton("Get Peer Clipboard")
        self.get_clipboard_btn.clicked.connect(self.get_clipboard)
        layout.addWidget(self.get_clipboard_btn)

        self.upload_btn = QPushButton("Upload File to Peer")
        self.upload_btn.clicked.connect(self.upload_file)
        layout.addWidget(self.upload_btn)

        self.setLayout(layout)

    def get_clipboard(self):
        try:
            r = requests.get(f"{PEER_URL}/clipboard")
            text = r.json().get("clipboard", "")
            self.clipboard_text.setText(text)
        except Exception as e:
            self.clipboard_text.setText("[Unable to fetch clipboard]")
            QMessageBox.warning(self, "Error", f"Failed to get clipboard:\n{e}")

    def upload_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File")
        if file_path:
            try:
                with open(file_path, 'rb') as f:
                    files = {'file': (os.path.basename(file_path), f)}
                    r = requests.post(f"{PEER_URL}/upload", files=files)
                    if r.status_code == 200:
                        QMessageBox.information(self, "Success", "File uploaded successfully!")
                    else:
                        raise Exception(r.text)
            except Exception as e:
                QMessageBox.critical(self, "Upload Failed", str(e))

# --- Main Entry Point ---
if __name__ == "__main__":
    os.makedirs(SHARED_FOLDER, exist_ok=True)

    threading.Thread(target=run_server, daemon=True).start()
    threading.Thread(target=clipboard_sync, daemon=True).start()

    app_qt = QApplication(sys.argv)
    window = ClipboardApp()
    window.show()
    sys.exit(app_qt.exec_())

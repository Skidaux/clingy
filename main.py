import threading, time, os
from flask import Flask, request, send_from_directory
import pyperclip
import tkinter as tk
from tkinter import filedialog, messagebox
import requests

# --- CONFIG ---
PEER_URL = "http://localhost:5000"  # Set this to the other PC's IP
SHARED_FOLDER = "./shared"          # Local folder to store received files

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
        except Exception as e:
            pass
        time.sleep(2)

# --- GUI App ---
class App:
    def __init__(self, root):
        self.root = root
        root.title("Clipboard & File Share")

        self.clip_label = tk.Label(root, text="Clipboard: ")
        self.clip_label.pack()

        self.upload_btn = tk.Button(root, text="Upload File", command=self.upload_file)
        self.upload_btn.pack()

        self.refresh_btn = tk.Button(root, text="Get Clipboard", command=self.get_clipboard)
        self.refresh_btn.pack()

    def upload_file(self):
        file_path = filedialog.askopenfilename()
        if file_path:
            try:
                with open(file_path, 'rb') as f:
                    files = {'file': (os.path.basename(file_path), f)}
                    r = requests.post(f"{PEER_URL}/upload", files=files)
                    messagebox.showinfo("Upload", "File uploaded successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Upload failed:\n{e}")

    def get_clipboard(self):
        try:
            r = requests.get(f"{PEER_URL}/clipboard")
            self.clip_label.config(text="Clipboard: " + r.json().get("clipboard", ""))
        except:
            self.clip_label.config(text="Clipboard: [unavailable]")

# --- MAIN ---
if __name__ == "__main__":
    os.makedirs(SHARED_FOLDER, exist_ok=True)

    threading.Thread(target=run_server, daemon=True).start()
    threading.Thread(target=clipboard_sync, daemon=True).start()

    root = tk.Tk()
    app = App(root)
    root.mainloop()

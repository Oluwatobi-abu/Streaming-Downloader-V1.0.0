import tkinter as tk
from tkinter import ttk, messagebox
import os, threading
import yt_dlp

# --- Downloads directory ---
DOWNLOADS_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# --- Path to bundled ffmpeg ---
ffmpeg_path = os.path.join(os.path.dirname(__file__), "ffmpeg_bin", "ffmpeg.exe")

def download_stream():
    page_url = entry_stream.get().strip()
    if not page_url:
        messagebox.showerror("Error", "Please enter a streaming page URL")
        return

    def run_download():
        try:
            def progress_hook(d):
                if d['status'] == 'downloading':
                    total = d.get('total_bytes') or d.get('total_bytes_estimate')
                    downloaded = d.get('downloaded_bytes', 0)
                    if total:
                        progress_bar["maximum"] = total
                        progress_bar["value"] = downloaded
                        percent = int(downloaded / total * 100)
                        percent_label.config(text=f"{percent}%")
                        root.update_idletasks()
                elif d['status'] == 'finished':
                    progress_bar["value"] = progress_bar["maximum"]
                    percent_label.config(text="100%")
                    root.update_idletasks()

            # --- yt-dlp options ---
            ydl_opts = {
                "outtmpl": f"{DOWNLOADS_DIR}/%(title)s.%(ext)s",
                "format": "best",
                "merge_output_format": "mp4",
                "progress_hooks": [progress_hook],
                "ffmpeg_location": ffmpeg_path,  # use bundled ffmpeg
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([page_url])

            messagebox.showinfo("Done", f"Downloaded and merged into {DOWNLOADS_DIR}")
        except Exception as e:
            messagebox.showerror("Error", f"Download failed: {e}")

    threading.Thread(target=run_download, daemon=True).start()

# --- Tkinter window ---
root = tk.Tk()
root.title("MyIDM Streaming Downloader")

tk.Label(root, text="Streaming Page URL (YouTube, etc.):").pack()
entry_stream = tk.Entry(root, width=50)
entry_stream.pack()
tk.Button(root, text="Download Stream", command=download_stream).pack(pady=10)

# Progress bar + percentage label
tk.Label(root, text="Download Progress:").pack()
progress_bar = ttk.Progressbar(root, length=400, mode="determinate")
progress_bar.pack(pady=5)
percent_label = tk.Label(root, text="0%")
percent_label.pack()

root.mainloop()
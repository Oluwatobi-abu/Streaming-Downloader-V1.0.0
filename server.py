from flask import Flask, request, jsonify
import os
from downloader import SegmentedDownloader, merge_audio_video

app = Flask(__name__)

DOWNLOADS_DIR = "downloads"
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

@app.post("/download")
def download():
    data = request.get_json(force=True)
    url = data.get("url")
    filename = data.get("filename") or os.path.basename(url.split("?")[0]) or "download.bin"
    path = os.path.join(DOWNLOADS_DIR, filename)

    SegmentedDownloader(url, path, segments=8).download()
    return jsonify({"status": "started", "file": path})

@app.post("/download_av")
def download_av():
    data = request.get_json(force=True)
    video_url = data.get("video_url")
    audio_url = data.get("audio_url")
    base_name = data.get("base_name") or "output"
    video_path = os.path.join(DOWNLOADS_DIR, base_name + ".video.mp4")
    audio_path = os.path.join(DOWNLOADS_DIR, base_name + ".audio.m4a")
    final_path = os.path.join(DOWNLOADS_DIR, base_name + ".mp4")

    SegmentedDownloader(video_url, video_path, segments=8).download()
    SegmentedDownloader(audio_url, audio_path, segments=8).download()
    merge_audio_video(video_path, audio_path, final_path)

    return jsonify({"status": "merged", "file": final_path})

if __name__ == "__main__":
    app.run(port=5000)
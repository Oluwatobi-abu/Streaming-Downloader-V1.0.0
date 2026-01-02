import yt_dlp

def get_streams(url):
    """
    Extract best video and audio URLs from a streaming site.
    Returns (video_url, audio_url, title).
    """
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "format": "bestvideo+bestaudio/best"
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formats = info.get("formats", [])
        video_url = next((f["url"] for f in formats if f.get("vcodec") != "none"), None)
        audio_url = next((f["url"] for f in formats if f.get("acodec") != "none" and f.get("vcodec") == "none"), None)
        title = info.get("title", "output")
        return video_url, audio_url, title
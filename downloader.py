import os
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ffmpeg_cmd = "ffmpeg"

import json
import math
import threading
from typing import List, Tuple, Optional, Callable
import requests
from tqdm import tqdm
import subprocess


class SegmentedDownloader:
    def __init__(self, url: str, output_path: str, segments: int = 8, segment_size: Optional[int] = None):
        self.url = url
        self.output_path = output_path
        self.tmp_path = output_path + ".part"
        self.meta_path = output_path + ".download.json"
        self.segments = segments
        self.segment_size = segment_size
        self.timeout = 60

    def _head(self):
        try:
            r = requests.head(self.url, timeout=self.timeout, allow_redirects=True, verify=False)
            r.raise_for_status()
        except Exception:
            # Fallback: use GET with stream=True
            r = requests.get(self.url, stream=True, timeout=self.timeout, allow_redirects=True, verify=False)
            r.raise_for_status()
        length = int(r.headers.get("Content-Length", 0))
        accept_ranges = r.headers.get("Accept-Ranges", "").lower() == "bytes"
        return length, accept_ranges

    def _plan_segments(self, total: int) -> List[Tuple[int, int]]:
        if self.segment_size:
            seg_size = self.segment_size
            count = math.ceil(total / seg_size)
        else:
            count = self.segments
            seg_size = math.ceil(total / count)
        ranges = []
        start = 0
        for _ in range(count):
            end = min(start + seg_size - 1, total - 1)
            ranges.append((start, end))
            start = end + 1
            if start >= total:
                break
        return ranges

    def _load_meta(self):
        if os.path.exists(self.meta_path):
            with open(self.meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"completed": []}

    def _save_meta(self, meta):
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f)

    def _preallocate(self, total: int):
        if not os.path.exists(self.tmp_path) or os.path.getsize(self.tmp_path) != total:
            with open(self.tmp_path, "wb") as f:
                f.truncate(total)

    # UPDATED: added progress_callback
    def _download_range(self, start: int, end: int, bar: Optional[tqdm], meta, progress_callback: Optional[Callable] = None):
        headers = {"Range": f"bytes={start}-{end}"}
        with requests.get(self.url, headers=headers, stream=True, timeout=self.timeout) as r:
            if r.status_code not in (206, 200):
                r.raise_for_status()
            with open(self.tmp_path, "r+b") as f:
                f.seek(start)
                for chunk in r.iter_content(chunk_size=1024 * 128):
                    if not chunk:
                        continue
                    pos = f.tell()
                    remaining = end - (pos - 1)
                    to_write = chunk if len(chunk) <= remaining + 1 else chunk[:remaining + 1]
                    f.write(to_write)
                    if bar:
                        bar.update(len(to_write))
                    if progress_callback:
                        progress_callback(len(to_write))  # notify GUI
                    if f.tell() - 1 >= end:
                        break
        meta["completed"].append([start, end])
        self._save_meta(meta)

    # UPDATED: download now accepts progress_callback
    def download(self, progress_callback: Optional[Callable] = None):
        total, accept_ranges = self._head()
        if total == 0:
            return self._fallback_single(progress_callback)
        if not accept_ranges:
            print("Range not supported; using single connection.")
            return self._fallback_single(progress_callback)

        ranges = self._plan_segments(total)
        meta = self._load_meta()
        completed = {tuple(x) for x in meta.get("completed", [])}
        pending = [r for r in ranges if tuple(r) not in completed]
        self._preallocate(total)

        already_downloaded = sum((end - start + 1) for start, end in completed)
        bar = None
        if not progress_callback:
            bar = tqdm(total=total, initial=already_downloaded, unit="B", unit_scale=True,
                       unit_divisor=1024, desc=os.path.basename(self.output_path))

        threads = []
        for start, end in pending:
            t = threading.Thread(target=self._download_range, args=(start, end, bar, meta, progress_callback), daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()
        if bar:
            bar.close()

        os.replace(self.tmp_path, self.output_path)
        if os.path.exists(self.meta_path):
            os.remove(self.meta_path)
        print("Downloaded:", self.output_path)
        return self.output_path

    def _fallback_single(self, progress_callback: Optional[Callable] = None):
        with requests.get(self.url, stream=True, timeout=self.timeout, verify=False) as r:
            r.raise_for_status()
            total = int(r.headers.get("Content-Length", 0)) or None
            if not progress_callback:
                with open(self.output_path, "wb") as f, tqdm(
                    total=total, unit="B", unit_scale=True, unit_divisor=1024, desc=os.path.basename(self.output_path)
                ) as bar:
                    for chunk in r.iter_content(chunk_size=1024 * 128):
                        if chunk:
                            f.write(chunk)
                            bar.update(len(chunk))
            else:
                with open(self.output_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 128):
                        if chunk:
                            f.write(chunk)
                            progress_callback(len(chunk))
        print("Downloaded:", self.output_path)
        return self.output_path


def merge_audio_video(video_file: str, audio_file: str, output_file: str):
    cmd = [
        ffmpeg_cmd, "-y",
        "-i", video_file,
        "-i", audio_file,
        "-c:v", "copy",
        "-c:a", "aac",
        output_file
    ]
    subprocess.run(cmd, check=True)
    print("Merged into:", output_file)


if __name__ == "__main__":
    subprocess.run("ffmpeg -version", shell=True, check=True)
    url = "https://speed.hetzner.de/1GB.bin"
    SegmentedDownloader(url, "test.bin", segments=4).download()
# ytdl.py – Local YouTube downloader

Small command-line tool built on **yt-dlp**. It downloads single videos,
Shorts, youtu.be short links and – optionally – playlists, and saves them as
`<title> [<video ID>].mp4` (or `.mp3` in audio-only mode) in the target folder.

## Installation

Python 3.10 or newer is required.

```bash
# 1. Install the dependency
pip install -r requirements.txt

# 2. Install ffmpeg (needed for merging video + audio and for MP3 export)
```

**Installing ffmpeg:**

- **Windows:** `winget install --id Gyan.FFmpeg -e` (or `choco install ffmpeg`).
  Open a new terminal afterwards. If `ffmpeg -version` does not work, add the
  directory containing `ffmpeg.exe` to your PATH variable.
- **macOS:** `brew install ffmpeg`
- **Linux:** `sudo apt install ffmpeg` (Debian/Ubuntu), `sudo dnf install ffmpeg`
  (Fedora) or `sudo pacman -S ffmpeg` (Arch).

Verify with:

```bash
ffmpeg -version
```

The tool checks for ffmpeg at startup and prints these instructions if it is missing.

## Usage

```
python ytdl.py [URL ...] [options]
```

| Option | Meaning |
| --- | --- |
| `--file FILE` | Read URLs from a text file (one per line, `#` = comment) |
| `-o, --output DIR` | Target folder, default `./downloads` |
| `-q, --quality {best,1080,720,480}` | Maximum quality, default `best` |
| `-a, --audio-only` | Audio only as MP3 (192 kbit/s) |
| `--format {mp4,mkv,webm,mov,avi}` | Video container, default `mp4` |
| `--playlist` | Allow playlists (without this flag only single videos) |

If no URLs are passed, the tool asks for links interactively; an empty line
ends the input.

### Three example calls

```bash
# 1) Single video into the default ./downloads folder
python ytdl.py https://youtu.be/dQw4w9WgXcQ

# 2) Several links from a file, 720p, custom target folder
python ytdl.py --file links.txt -q 720 -o C:\Videos

# 3) Two Shorts as MP3 only, allow playlist links
python ytdl.py https://www.youtube.com/shorts/abc12345678 https://www.youtube.com/shorts/xyz98765432 -a --playlist
```

Example `links.txt`:

```text
# My watchlist
https://www.youtube.com/watch?v=dQw4w9WgXcQ
https://youtu.be/abc12345678
```

## Behaviour

- **Progress:** For each download a bar with percentage, speed and remaining
  time, preceded by the overall overview (`Video 2 of 5`).
- **Archive:** `download-archive.txt` in the target folder. Already downloaded
  IDs are skipped – deleting this file resets the archive.
- **Errors:** Private, deleted, region-blocked or age-restricted videos are
  reported and the rest of the list continues. Network errors are retried up to
  three times.
- **File names:** The title is cleaned to be safe on Windows and Unix; the
  video ID is in square brackets.

## Testing

1. **Check installation:** `python -c "import yt_dlp; print('ok')"` and
   `ffmpeg -version`.
2. **Show help:** `python ytdl.py --help` – all options should appear.
3. **Interactive mode:** Run `python ytdl.py`, paste a link and finish with an
   empty line.
4. **Real video:** Download a short public video and check that
   `<title> [<ID>].mp4` is in the target folder.
5. **Skip logic:** Enter the same link again – it should say “Already
   downloaded (archive), skipped”.
6. **Error case:** Mix a deliberately invalid link (e.g. `https://example.com/foo`)
   with a private one; both must be reported without stopping the rest.
7. **Audio mode:** Use `-a` and verify that an `.mp3` is created.

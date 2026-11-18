# ytdl.py – lokaler YouTube-Downloader

Kleines Kommandozeilen-Tool auf Basis von **yt-dlp**. Es lädt einzelne Videos,
Shorts, youtu.be-Kurzlinks und – optional – Playlists herunter und speichert sie
als `<Titel> [<Video-ID>].mp4` (bzw. `.mp3` im Audio-Modus) im Zielordner.

## Installation

Python 3.10 oder neuer wird benötigt.

```bash
# 1. Abhängigkeit installieren
pip install -r requirements.txt

# 2. ffmpeg installieren (wird für das Zusammenführen von Video+Audio und MP3 benötigt)
```

**ffmpeg installieren:**

- **Windows:** `winget install --id Gyan.FFmpeg -e` (oder `choco install ffmpeg`).
  Danach ein neues Terminal öffnen. Falls `ffmpeg -version` nicht funktioniert,
  das Verzeichnis mit `ffmpeg.exe` zur PATH-Variable hinzufügen.
- **macOS:** `brew install ffmpeg`
- **Linux:** `sudo apt install ffmpeg` (Debian/Ubuntu), `sudo dnf install ffmpeg`
  (Fedora) oder `sudo pacman -S ffmpeg` (Arch).

Prüfen mit:

```bash
ffmpeg -version
```

Das Tool prüft ffmpeg beim Start automatisch und gibt bei Fehlen diese Anleitung aus.

## Verwendung

```
python ytdl.py [URL ...] [Optionen]
```

| Option | Bedeutung |
| --- | --- |
| `--file DATEI` | URLs aus einer Textdatei lesen (eine pro Zeile, `#` = Kommentar) |
| `-o, --output ORDNER` | Zielordner, Standard `./downloads` |
| `-q, --quality {best,1080,720,480}` | Maximale Qualität, Standard `best` |
| `-a, --audio-only` | Nur Audio als MP3 (192 kbit/s) |
| `--format {mp4,mkv,webm,mov,avi}` | Video-Container, Standard `mp4` |
| `--playlist` | Playlists erlauben (ohne Flag nur Einzelvideos) |

Ohne übergebene URLs fragt das Tool interaktiv nach Links; eine leere Zeile
beendet die Eingabe.

### Drei Beispielaufrufe

```bash
# 1) Einzelvideo in den Standardordner ./downloads
python ytdl.py https://youtu.be/dQw4w9WgXcQ

# 2) Mehrere Links aus einer Datei, 720p, eigener Zielordner
python ytdl.py --file links.txt -q 720 -o C:\Videos

# 3) Zwei Shorts nur als MP3, Playlist-Links erlauben
python ytdl.py https://www.youtube.com/shorts/abc12345678 https://www.youtube.com/shorts/xyz98765432 -a --playlist
```

Beispiel für `links.txt`:

```text
# Meine Merkliste
https://www.youtube.com/watch?v=dQw4w9WgXcQ
https://youtu.be/abc12345678
```

## Verhalten

- **Fortschritt:** Pro Download Balken mit Prozent, Geschwindigkeit und Restzeit,
  davor die Gesamtübersicht (`Video 2 von 5`).
- **Archiv:** Im Zielordner liegt `download-archive.txt`. Bereits geladene IDs
  werden übersprungen – löschen dieser Datei setzt den Archivstand zurück.
- **Fehler:** Private, gelöschte, regional gesperrte oder altersbeschränkte Videos
  werden gemeldet, der Rest der Liste läuft weiter. Netzwerkfehler werden bis zu
  dreimal wiederholt.
- **Dateinamen:** Der Titel wird zu einem windows- und unix-sicheren Namen
  bereinigt; die Video-ID steht in eckigen Klammern.

## Testen

1. **Installation prüfen:** `python -c "import yt_dlp; print('ok')"` und
   `ffmpeg -version`.
2. **Hilfe anzeigen:** `python ytdl.py --help` – alle Optionen müssen erscheinen.
3. **Interaktiver Modus:** `python ytdl.py` starten, einen Link einfügen und mit
   einer leeren Zeile abschließen.
4. **Echtes Video:** Ein kurzes, öffentliches Video herunterladen und kontrollieren,
   ob `<Titel> [<ID>].mp4` im Zielordner liegt.
5. **Skip-Logik:** Denselben Link erneut eingeben – es muss „Bereits
   heruntergeladen (Archiv), übersprungen“ erscheinen.
6. **Fehlerfall:** Bewusst ungültigen Link (z. B. `https://example.com/foo`) und
   einen privaten Link mischen; beide müssen gemeldet werden, ohne dass der Rest
   abbricht.
7. **Audio-Modus:** `-a` verwenden und prüfen, dass eine `.mp3` entsteht.

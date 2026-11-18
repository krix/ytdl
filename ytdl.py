"""Lokaler YouTube-Downloader auf Basis von yt-dlp.

Aufruf: python ytdl.py [URL ...] [Optionen]
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, urlparse

try:
    import yt_dlp
except ImportError:  # pragma: no cover - nur bei fehlender Installation
    sys.exit(
        "Fehler: 'yt-dlp' ist nicht installiert.\n"
        "Bitte zuerst: pip install -r requirements.txt"
    )


FFMPEG_HINWEIS = """Fehler: ffmpeg wurde nicht gefunden.

ffmpeg wird zum Zusammenführen von Video- und Audiospuren (und für MP3-Export)
benötigt. Bitte installieren und anschließend die PATH-Variable prüfen:

  Windows (PowerShell, mit winget):
      winget install --id Gyan.FFmpeg -e
      Alternativ mit Chocolatey: choco install ffmpeg
      Danach: neues Terminal öffnen und "ffmpeg -version" testen.
      Falls nötig: ffmpeg.exe-Verzeichnis manuell zu PATH hinzufügen
      (Einstellungen -> System -> Umgebungsvariablen -> Pfad).

  macOS (Homebrew):
      brew install ffmpeg
      Danach: ffmpeg -version

  Linux (Beispiele):
      Debian/Ubuntu:  sudo apt update && sudo apt install ffmpeg
      Fedora:         sudo dnf install ffmpeg
      Arch:           sudo pacman -S ffmpeg

Nach der Installation dieses Skript erneut starten.
"""

HOSTS = {"youtube.com", "youtube-nocookie.com", "music.youtube.com", "youtu.be"}
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
PLAYLIST_ID = re.compile(r"^[A-Za-z0-9_-]+$")
QUALITAETEN = {"best": None, "1080": 1080, "720": 720, "480": 480}


@dataclass
class Bericht:
    """Zählt die Ergebnisse aller Downloads."""

    erfolgreich: int = 0
    uebersprungen: int = 0
    fehlgeschlagen: list[tuple[str, str]] = field(default_factory=list)


class YtdlLogger:
    """Fängt yt-dlp-Meldungen ab und erkennt Archiv-Skips."""

    def __init__(self, bericht: Bericht) -> None:
        self.bericht = bericht

    def debug(self, nachricht: Any) -> None:
        text = str(nachricht)
        if "has already been recorded in the archive" in text:
            self.bericht.uebersprungen += 1
            print("  → Bereits heruntergeladen (Archiv), übersprungen.")

    def info(self, nachricht: Any, *args: Any, **kwargs: Any) -> None:
        pass

    def warning(self, nachricht: Any, *args: Any, **kwargs: Any) -> None:
        print(f"  Hinweis: {nachricht}", file=sys.stderr)

    def error(self, nachricht: Any, *args: Any, **kwargs: Any) -> None:
        # Details werden über die Exception erfasst; hier nichts doppelt drucken.
        pass


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Definition und Auswertung der Kommandozeilenoptionen."""
    parser = argparse.ArgumentParser(
        description="YouTube-Videos lokal herunterladen (yt-dlp + ffmpeg).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Beispiele:\n"
            "  python ytdl.py https://youtu.be/dQw4w9WgXcQ\n"
            "  python ytdl.py --file links.txt -q 720 -o C:\\Videos\n"
            "  python ytdl.py URL1 URL2 -a --format mp4\n"
        ),
    )
    parser.add_argument("urls", nargs="*", metavar="URL", help="ein oder mehrere YouTube-Links")
    parser.add_argument("--file", metavar="DATEI", help="Textdatei mit einer URL pro Zeile (# = Kommentar)")
    parser.add_argument("-o", "--output", default="./downloads", metavar="ORDNER", help="Zielordner (Standard: ./downloads)")
    parser.add_argument("-q", "--quality", choices=("best", "1080", "720", "480"), default="best", help="maximale Videoqualität (Standard: best)")
    parser.add_argument("-a", "--audio-only", action="store_true", help="nur Audio als MP3 extrahieren")
    parser.add_argument("--format", dest="container", choices=("mp4", "mkv", "webm", "mov", "avi"), default="mp4", help="Container für Videos (Standard: mp4)")
    parser.add_argument("--playlist", action="store_true", help="auch Playlists herunterladen (Standard: nur Einzelvideos)")
    return parser.parse_args(argv)


def _host(url: str) -> str:
    """Hostname ohne www./m.-Präfix."""
    host = (urlparse(url).hostname or "").lower()
    for prefix in ("www.", "m."):
        if host.startswith(prefix):
            return host[len(prefix):]
    return host


def _normalisiere(url: str) -> str:
    """Ergänzt ein fehlendes https:// und entfernt Leerzeichen."""
    url = url.strip()
    if url and not url.lower().startswith(("http://", "https://")):
        return "https://" + url
    return url


def video_id(url: str) -> str | None:
    """Video-ID aus Watch-, Shorts-, Embed- oder youtu.be-Links holen."""
    parsed = urlparse(url)
    host = _host(url)
    teile = [t for t in parsed.path.split("/") if t]

    if host == "youtu.be":
        return teile[0] if teile else None
    if host not in HOSTS:
        return None
    if teile and teile[0] in ("shorts", "embed") and len(teile) >= 2:
        return teile[1]
    if parsed.path == "/watch":
        return parse_qs(parsed.query).get("v", [None])[0]
    return None


def ist_playlist(url: str) -> bool:
    """Prüft, ob die URL eine YouTube-Playlist referenziert."""
    parsed = urlparse(url)
    return _host(url) == "youtube.com" and parsed.path == "/playlist" and bool(
        parse_qs(parsed.query).get("list")
    )


def validiere_urls(
    urls: Iterable[str], *, playlists_erlaubt: bool
) -> tuple[list[str], list[tuple[str, str]]]:
    """Trennt gültige von ungültigen URLs und liefert Begründungen."""
    gueltig: list[str] = []
    ungueltig: list[tuple[str, str]] = []

    for roh in urls:
        url = _normalisiere(roh)
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or _host(url) not in HOSTS:
            ungueltig.append((roh, "keine gültige YouTube-URL"))
            continue

        vid = video_id(url)
        if vid and VIDEO_ID.fullmatch(vid):
            gueltig.append(url)
            continue

        if ist_playlist(url):
            playlist_id = parse_qs(parsed.query)["list"][0]
            if playlists_erlaubt and PLAYLIST_ID.fullmatch(playlist_id):
                gueltig.append(url)
            elif not playlists_erlaubt:
                ungueltig.append((roh, "Playlist-Link – bitte --playlist verwenden"))
            else:
                ungueltig.append((roh, "ungültige Playlist-ID"))
            continue

        ungueltig.append((roh, "Video-ID fehlt oder ist ungültig"))

    return gueltig, ungueltig


def sammle_urls(args: argparse.Namespace) -> list[str]:
    """URLs aus Argumenten, Datei und ggf. interaktiver Eingabe sammeln."""
    urls = list(args.urls)

    if args.file:
        datei = Path(args.file).expanduser()
        if not datei.is_file():
            sys.exit(f"Fehler: Datei {datei} wurde nicht gefunden.")
        for zeile in datei.read_text(encoding="utf-8").splitlines():
            zeile = zeile.strip()
            if zeile and not zeile.startswith("#"):
                urls.append(zeile)

    if not urls:
        print("Keine URLs übergeben. Bitte Links eingeben (leere Zeile beendet die Eingabe):")
        while True:
            try:
                zeile = input("URL> ").strip()
            except EOFError:
                break
            if not zeile:
                break
            urls.append(zeile)

    return urls


def ffmpeg_pruefen() -> None:
    """Beendet das Programm mit einer Installationsanleitung, falls ffmpeg fehlt."""
    if shutil.which("ffmpeg") is None:
        sys.exit(FFMPEG_HINWEIS)


def format_selector(args: argparse.Namespace) -> str:
    """yt-dlp-Formatauswahl für Qualität und Container bauen."""
    if args.audio_only:
        return "bestaudio/best"

    hoehe = QUALITAETEN[args.quality]
    if hoehe:
        if args.container == "mp4":
            return (
                f"bestvideo[height<={hoehe}][ext=mp4]+bestaudio[ext=m4a]/"
                f"bestvideo[height<={hoehe}]+bestaudio/best[height<={hoehe}]"
            )
        return f"bestvideo[height<={hoehe}]+bestaudio/best[height<={hoehe}]"

    basis = "bestvideo+bestaudio/best"
    if args.container == "mp4":
        return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
    return basis


def _geschwindigkeit(speed: float | None) -> str:
    if not speed:
        return "? MiB/s"
    if speed >= 1024 * 1024:
        return f"{speed / 1024 / 1024:.1f} MiB/s"
    return f"{speed / 1024:.0f} KiB/s"


def _restzeit(eta: float | None) -> str:
    if eta is None:
        return "--:--"
    eta = int(eta)
    return f"{eta // 60:02d}:{eta % 60:02d}"


def fortschritt_hook(index: int, gesamt: int):
    """Erzeugt einen yt-dlp-Progress-Hook mit Balken, Tempo und Restzeit."""

    def hook(daten: dict[str, Any]) -> None:
        if daten.get("status") == "downloading":
            geladen = daten.get("downloaded_bytes") or 0
            gesamt_bytes = daten.get("total_bytes") or daten.get("total_bytes_estimate") or 0
            prozent = min(100.0, geladen / gesamt_bytes * 100) if gesamt_bytes else 0.0
            breite = 24
            gefuellt = min(breite - 1, int(breite * prozent / 100))
            balken = "=" * gefuellt + ">" + "." * (breite - gefuellt - 1)
            print(
                f"\r  [{balken}] {prozent:5.1f}% | "
                f"{_geschwindigkeit(daten.get('speed'))} | verbleibend {_restzeit(daten.get('eta'))}",
                end="",
                flush=True,
            )
        elif daten.get("status") == "finished":
            print()

    return hook


def ydl_optionen(
    args: argparse.Namespace,
    ziel: Path,
    bericht: Bericht,
    index: int,
    gesamt: int,
) -> dict[str, Any]:
    """yt-dlp-Optionen für einen Download zusammenstellen."""
    optionen: dict[str, Any] = {
        "format": format_selector(args),
        # '#S' bereinigt den Titel streng (Windows-sicher), die eckigen Klammern
        # bleiben als Literal im Template erhalten.
        "outtmpl": str(ziel / "%(title)#S [%(id)S].%(ext)s"),
        "download_archive": str(ziel / "download-archive.txt"),
        "noplaylist": not args.playlist,
        "quiet": True,
        "noprogress": True,
        "logger": YtdlLogger(bericht),
        "progress_hooks": [fortschritt_hook(index, gesamt)],
        "retries": 3,
        "fragment_retries": 3,
        "socket_timeout": 15,
    }
    if args.audio_only:
        optionen["postprocessors"] = [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
        ]
    else:
        optionen["merge_output_format"] = args.container
    return optionen


def fehler_text(meldung: str) -> str:
    """Typische yt-dlp-Fehler in verständliches Deutsch übersetzen."""
    text = meldung.lower()
    if "sign in to confirm" in text or "age" in text:
        return "Altersbeschränkung: Anmeldung/Verifizierung erforderlich"
    if "private" in text:
        return "Video ist privat"
    if "not available in your country" in text or "geo" in text or "region" in text:
        return "Video ist regional gesperrt"
    if "unavailable" in text or "removed" in text or "deleted" in text or "not found" in text:
        return "Video wurde gelöscht oder ist nicht verfügbar"
    if "unable to download" in text or "connection" in text or "timed out" in text:
        return "Netzwerkfehler auch nach 3 Wiederholungsversuchen"
    return " ".join(meldung.split())[:300]


def laden(
    url: str,
    args: argparse.Namespace,
    ziel: Path,
    bericht: Bericht,
    index: int,
    gesamt: int,
) -> None:
    """Eine URL herunterladen; Fehler wirken sich nicht auf andere URLs aus."""
    optionen = ydl_optionen(args, ziel, bericht, index, gesamt)
    skips_vorher = bericht.uebersprungen
    try:
        with yt_dlp.YoutubeDL(optionen) as ydl:
            ydl.download([url])
    except yt_dlp.utils.DownloadError as exc:
        bericht.fehlgeschlagen.append((url, fehler_text(str(exc))))
    except KeyboardInterrupt:
        print("\nDownload durch Benutzer abgebrochen.")
        raise SystemExit(130)
    except Exception as exc:  # defensiv: ein Video darf die Liste nie abbrechen
        bericht.fehlgeschlagen.append((url, fehler_text(f"{type(exc).__name__}: {exc}")))
    else:
        if bericht.uebersprungen == skips_vorher:
            bericht.erfolgreich += 1


def bericht_ausgeben(bericht: Bericht, ziel: Path) -> None:
    """Abschlussübersicht mit Zählern, Fehlern und Speicherort drucken."""
    print("\n" + "=" * 64)
    print("Abschlussbericht")
    print("=" * 64)
    print(f"Erfolgreich:     {bericht.erfolgreich}")
    print(f"Übersprungen:    {bericht.uebersprungen}")
    print(f"Fehlgeschlagen:  {len(bericht.fehlgeschlagen)}")
    print(f"Speicherort:     {ziel}")
    if bericht.fehlgeschlagen:
        print("\nFehlgeschlagene Downloads:")
        for url, grund in bericht.fehlgeschlagen:
            print(f"  - {url}")
            print(f"      Grund: {grund}")


def main(argv: list[str] | None = None) -> int:
    """Einstiegspunkt: Optionen lesen, URLs prüfen, Downloads ausführen."""
    args = parse_args(argv)
    ffmpeg_pruefen()

    ziel = Path(args.output).expanduser().resolve()
    ziel.mkdir(parents=True, exist_ok=True)

    bericht = Bericht()
    gueltig, ungueltig = validiere_urls(sammle_urls(args), playlists_erlaubt=args.playlist)

    for url, grund in ungueltig:
        print(f"Ungültige URL übersprungen: {url!r} ({grund})")
        bericht.fehlgeschlagen.append((url, f"ungültige URL: {grund}"))

    if not gueltig:
        bericht_ausgeben(bericht, ziel)
        return 1

    print(f"{len(gueltig)} gültige URL(s) – Zielordner: {ziel}")
    for index, url in enumerate(gueltig, start=1):
        print(f"\nVideo {index} von {len(gueltig)}: {url}")
        laden(url, args, ziel, bericht, index, len(gueltig))

    bericht_ausgeben(bericht, ziel)
    return 1 if bericht.fehlgeschlagen else 0


if __name__ == "__main__":
    raise SystemExit(main())

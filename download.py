from yt_dlp import YoutubeDL
import os
import re
import sys
import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from kivy.uix.checkbox import CheckBox
from kivy.uix.scrollview import ScrollView
from kivy.uix.progressbar import ProgressBar
from kivy.clock import Clock
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
import threading
from typing import Optional, List, Dict, Tuple
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache


@lru_cache(maxsize=128)
def get_url_info(url: str) -> Tuple[str, Dict]:
    """
    Get URL information with caching to avoid duplicate yt-dlp calls.
    Returns (content_type, info_dict) for efficient reuse.

    Args:
        url (str): YouTube URL to analyze

    Returns:
        Tuple[str, Dict]: (content_type, info_dict) where content_type is 'video', 'playlist', or 'channel'
    """
    try:
        # Use yt-dlp to extract info without downloading
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,  # Only extract basic info, faster
            'no_warnings': True,
            'skip_download': True,
            'playlist_items': '1',  # Only check first item for speed
        }

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            # Check if info extraction was successful
            if info is None:
                # Fallback to URL parsing if yt-dlp fails
                parsed_url = urlparse(url)
                query_params = parse_qs(parsed_url.query)

                # Check for channel patterns
                if '/@' in url or '/channel/' in url or '/c/' in url or '/user/' in url:
                    return 'channel', {}
                elif 'list' in query_params:
                    return 'playlist', {}
                else:
                    return 'video', {}

            # Determine content type based on yt-dlp info
            content_type = info.get('_type', 'video')

            # Handle channel detection
            if content_type == 'playlist':
                # Check if it's actually a channel (uploader_id indicates channel content)
                if info.get('uploader_id') and ('/@' in url or '/channel/' in url or '/c/' in url or '/user/' in url):
                    return 'channel', info
                else:
                    return 'playlist', info

            return content_type, info

    except Exception:
        # Simple fallback: check URL patterns
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)

        if '/@' in url or '/channel/' in url or '/c/' in url or '/user/' in url:
            return 'channel', {}
        elif 'list' in query_params:
            return 'playlist', {}
        else:
            return 'video', {}


def is_playlist_url(url: str) -> bool:
    """
    Check if the provided URL is a playlist or a single video using cached detection.
    Uses yt-dlp's native detection with simple URL parsing fallback.

    Args:
        url (str): YouTube URL to check

    Returns:
        bool: True if URL is a playlist, False if single video
    """
    content_type, _ = get_url_info(url)
    return content_type == 'playlist'


def get_content_type(url: str) -> str:
    """
    Get the content type of a YouTube URL.

    Args:
        url (str): YouTube URL to analyze

    Returns:
        str: 'video', 'playlist', or 'channel'
    """
    content_type, _ = get_url_info(url)
    return content_type


def parse_multiple_urls(input_string: str) -> List[str]:
    """
    Parse multiple URLs from input string separated by commas, spaces, newlines, or mixed formats.
    Handles complex mixed separators like "url1, url2 url3\nurl4".

    Args:
        input_string (str): String containing one or more URLs

    Returns:
        List[str]: List of cleaned URLs
    """
    # Use regex to split by multiple separators: comma, space, newline, tab
    urls = re.split(r'[,\s\n\t]+', input_string.strip())
    urls = [url.strip() for url in urls if url.strip()]

    # Validate URLs (basic YouTube URL check)
    valid_urls = []
    invalid_count = 0
    for url in urls:
        if ('youtube.com' in url or 'youtu.be' in url) and (
            '/watch?' in url or
            '/playlist?' in url or
            '/@' in url or
            '/channel/' in url or
            '/c/' in url or
            '/user/' in url or
            'youtu.be/' in url
        ):
            valid_urls.append(url)
        elif url:  # Only show warning for non-empty strings
            print(f"Warning: Skipping invalid URL: {url}")
            invalid_count += 1

    if invalid_count > 0:
        print(
            f"Info: Found {len(valid_urls)} valid YouTube URLs, skipped {invalid_count} invalid entries")

    return valid_urls


def download_single_video(url: str, output_path: str, thread_id: int = 0, audio_only: bool = False, quality: str = "best") -> dict:
    """
    Download a single YouTube video, playlist, or channel.

    Args:
        url (str): YouTube URL to download (video, playlist, or channel)
        output_path (str): Directory to save the download
        thread_id (int): Thread identifier for logging
        audio_only (bool): If True, download audio only in MP3 format

    Returns:
        dict: Result status with success/failure info
    """
    if audio_only:
        # Configure for audio-only MP3 downloads
        quality_map = {
            '320kbps': '320',
            '256kbps': '256',
            '192kbps': '192',
            '128kbps': '128',
            '64kbps': '64'
        }
        audio_quality = quality_map.get(quality, '192')
        format_selector = 'bestaudio/best'
        file_extension = 'mp3'
        postprocessors = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': audio_quality,
        }]
        print(f"[Thread {thread_id}] Audio-only mode: Downloading MP3 at {audio_quality}kbps...")
    else:
        # Configure for video downloads
        quality_map = {
            '1080p': '1080',
            '720p': '720',
            '480p': '480',
            '360p': '360',
            '240p': '240'
        }
        video_height = quality_map.get(quality, '1080')
        format_selector = (
            # Prefer formats that already include audio at specified quality
            f'best[height<={video_height}]/'
            # Fallback to merging if needed
            f'bestvideo[height<={video_height}]+bestaudio/best'
        )
        file_extension = 'mp4'
        postprocessors = [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }]
        print(f"[Thread {thread_id}] Video mode: Downloading MP4 at {quality}...")

    # Configure yt-dlp options
    ydl_opts = {
        'format': format_selector,
        'ignoreerrors': True,
        'no_warnings': False,
        'extract_flat': False,
        # Disable additional downloads for clean output
        'writesubtitles': False,
        'writethumbnail': False,
        'writeautomaticsub': False,
        'postprocessors': postprocessors,
        # Clean up options
        'keepvideo': False,
        'clean_infojson': True,
        'retries': 3,
        'fragment_retries': 3,
        # Ensure playlists are fully downloaded
        'noplaylist': False,  # Allow playlist downloads
    }

    # Add merge format for video downloads only
    if not audio_only:
        ydl_opts['merge_output_format'] = 'mp4'

    # Set different output templates for playlists, channels and single videos
    content_type, cached_info = get_url_info(url)

    if content_type == 'playlist':
        ydl_opts['outtmpl'] = os.path.join(
            output_path, '%(playlist_title)s', f'%(playlist_index)s-%(title)s.{file_extension}')
        print(
            f"[Thread {thread_id}] Detected playlist URL. Downloading entire playlist...")
    elif content_type == 'channel':
        ydl_opts['outtmpl'] = os.path.join(
            output_path, '%(uploader)s', f'%(upload_date)s-%(title)s.{file_extension}')
        print(
            f"[Thread {thread_id}] Detected channel URL. Downloading entire channel...")
    else:  # single video
        ydl_opts['outtmpl'] = os.path.join(
            output_path, f'%(title)s.{file_extension}')
        print(
            f"[Thread {thread_id}] Detected single video URL. Downloading {'audio' if audio_only else 'video'}...")

    try:
        with YoutubeDL(ydl_opts) as ydl:
            # Extract fresh info for download (cached info is only for detection)
            info = ydl.extract_info(url, download=False)

            # Check if info extraction was successful
            if info is None:
                return {
                    'url': url,
                    'success': False,
                    'message': f"[Thread {thread_id}] Failed to extract video information. Video may be private or unavailable."
                }

            if info.get('_type') == 'playlist':
                title = info.get('title', 'Unknown Playlist')
                video_count = len(info.get('entries', []))
                print(
                    f"[Thread {thread_id}] {content_type.title()}: '{title}' ({video_count} videos)")

                # Ensure we have entries to download
                if video_count == 0:
                    return {
                        'url': url,
                        'success': False,
                        'message': f"[Thread {thread_id}] {content_type.title()} appears to be empty or private"
                    }

            # Download content
            ydl.download([url])

            if info.get('_type') == 'playlist':
                title = info.get('title', f'Unknown {content_type.title()}')
                video_count = len(info.get('entries', []))
                return {
                    'url': url,
                    'success': True,
                    'message': f"[Thread {thread_id}] {content_type.title()} '{title}' download completed! ({video_count} {'MP3s' if audio_only else 'videos'})"
                }
            else:
                return {
                    'url': url,
                    'success': True,
                    'message': f"[Thread {thread_id}] {'Audio' if audio_only else 'Video'} download completed successfully!"
                }

    except Exception as e:
        return {
            'url': url,
            'success': False,
            'message': f"[Thread {thread_id}] Error: {str(e)}"
        }


def download_youtube_content(urls: List[str], output_path: Optional[str] = None,
                              max_workers: int = 3, audio_only: bool = False, quality: str = "best") -> None:
    """
    Download YouTube content (single videos, playlists, or channels) in MP4 format or MP3 audio only.
    Supports multiple URLs for simultaneous downloading.

    Args:
        urls (List[str]): List of YouTube URLs to download (videos, playlists, or channels)
        output_path (str, optional): Directory to save the downloads. Defaults to './downloads'
        max_workers (int): Maximum number of concurrent downloads
        audio_only (bool): If True, download audio only in MP3 format
    """
    # Set default output path if none provided
    if output_path is None:
        output_path = os.path.join(os.getcwd(), 'downloads')

    # Create output directory if it doesn't exist
    os.makedirs(output_path, exist_ok=True)

    print(
        f"\nStarting download of {len(urls)} URL(s) with {max_workers} concurrent workers...")
    print(f"Output directory: {output_path}")
    print(f"Format: {'MP3 Audio Only' if audio_only else 'MP4 Video'}")

    # Show what types of content we're downloading
    playlist_count = sum(
        1 for url in urls if get_content_type(url) == 'playlist')
    channel_count = sum(
        1 for url in urls if get_content_type(url) == 'channel')
    video_count = len(urls) - playlist_count - channel_count

    content_summary = []
    if playlist_count > 0:
        content_summary.append(f"{playlist_count} playlist(s)")
    if channel_count > 0:
        content_summary.append(f"{channel_count} channel(s)")
    if video_count > 0:
        content_summary.append(f"{video_count} video(s)")

    if content_summary:
        print(f"Content: {' + '.join(content_summary)}")
    else:
        print("Content: Unknown content type")

    print("-" * 60)

    # Concurrent downloads
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {
            executor.submit(download_single_video, url, output_path, i+1, audio_only, quality): url
            for i, url in enumerate(urls)
        }

        # Collect results
        for future in as_completed(future_to_url):
            result = future.result()
            results.append(result)
            print(result['message'])

    print("\n" + "=" * 60)
    print("DOWNLOAD SUMMARY")
    print("=" * 60)

    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]

    print(f"Successful downloads: {len(successful)}")
    print(f"Failed downloads: {len(failed)}")

    if failed:
        print("\nFailed URLs:")
        for result in failed:
            print(f"   • {result['url']}")
            print(f"     Reason: {result['message']}")

    if successful:
        print(f"\nAll files saved to: {output_path}")


class YouTubeDownloaderGUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = 10
        self.spacing = 10

        # URL input
        self.add_widget(Label(text="YouTube URLs:", size_hint_y=None, height=30))
        self.add_widget(Label(
            text="Pega aquí las URLs de YouTube (una por línea o separadas por comas)",
            size_hint_y=None,
            height=20,
            font_size=12,
            color=(0.5, 0.5, 0.5, 1)
        ))
        self.url_text = TextInput(
            text="",
            multiline=True,
            size_hint_y=None,
            height=60
        )
        self.add_widget(self.url_text)

        # Output directory
        output_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        output_layout.add_widget(Label(text="Directorio de salida:", size_hint_x=0.3))
        self.output_entry = TextInput(
            text=os.path.join(os.getcwd(), 'downloads'),
            size_hint_x=0.6
        )
        output_layout.add_widget(self.output_entry)
        browse_btn = Button(text="Buscar", size_hint_x=0.1)
        browse_btn.bind(on_press=self.browse_directory)
        output_layout.add_widget(browse_btn)
        self.add_widget(output_layout)

        # Format selection
        self.add_widget(Label(text="Formato:", size_hint_y=None, height=30))
        format_layout = BoxLayout(size_hint_y=None, height=60, spacing=20)
        self.format_var = "video"

        video_layout = BoxLayout(spacing=5)
        self.video_cb = CheckBox(group='format', active=True)
        self.video_cb.bind(active=self.on_format_change)
        video_layout.add_widget(self.video_cb)
        video_layout.add_widget(Label(text="Video (MP4)"))
        format_layout.add_widget(video_layout)

        audio_layout = BoxLayout(spacing=5)
        self.audio_cb = CheckBox(group='format')
        self.audio_cb.bind(active=self.on_format_change)
        audio_layout.add_widget(self.audio_cb)
        audio_layout.add_widget(Label(text="Audio (MP3)"))
        format_layout.add_widget(audio_layout)

        self.add_widget(format_layout)

        # Quality selection
        self.add_widget(Label(text="Calidad:", size_hint_y=None, height=30))
        quality_layout = BoxLayout(size_hint_y=None, height=40, spacing=10)
        quality_layout.add_widget(Label(text="Calidad:", size_hint_x=0.3))
        self.quality_spinner = Spinner(
            text='1080p',
            values=('1080p', '720p', '480p', '360p', '240p'),
            size_hint_x=0.7
        )
        quality_layout.add_widget(self.quality_spinner)
        self.add_widget(quality_layout)

        # Initialize quality options for default video format
        self.on_format_change(self.video_cb, True)

        # Concurrent workers (automatic)
        self.add_widget(Label(
            text="Descargas concurrentes: Automáticas (basado en cantidad de URLs)",
            size_hint_y=None,
            height=30,
            font_size=12,
            color=(0.5, 0.5, 0.5, 1)
        ))

        # Buttons layout
        buttons_layout = BoxLayout(size_hint_y=None, height=50, spacing=10)

        self.start_button = Button(
            text="Iniciar Descarga",
            size_hint_x=1,
            background_color=(0.2, 0.6, 0.2, 1)
        )
        self.start_button.bind(on_press=self.start_download)
        buttons_layout.add_widget(self.start_button)

        self.add_widget(buttons_layout)

        # Progress bar
        self.progress = ProgressBar(max=100, size_hint_y=None, height=20)
        self.add_widget(self.progress)

        # Log area
        self.add_widget(Label(text="Registro de progreso:", size_hint_y=None, height=30))
        scroll_view = ScrollView(size_hint_y=0.4)
        self.log_text = TextInput(
            readonly=True,
            multiline=True,
            size_hint=(1, None),
            height=200
        )
        scroll_view.add_widget(self.log_text)
        self.add_widget(scroll_view)

    def on_format_change(self, checkbox, value):
        if value:
            if checkbox == self.video_cb:
                self.format_var = "video"
                self.quality_spinner.values = ('1080p', '720p', '480p', '360p', '240p')
                self.quality_spinner.text = '1080p'
            elif checkbox == self.audio_cb:
                self.format_var = "audio"
                self.quality_spinner.values = ('320kbps', '256kbps', '192kbps', '128kbps', '64kbps')
                self.quality_spinner.text = '192kbps'

    def log_message(self, message):
        Clock.schedule_once(lambda dt: self._update_log(message))

    def _update_log(self, message):
        self.log_text.text += message + "\n"
        self.log_text.cursor = (0, len(self.log_text.text.split('\n')))

    def start_download(self, instance):
        urls_input = self.url_text.text.strip()
        if not urls_input.strip():
            self.show_error("Por favor ingresa al menos una URL.")
            return

        urls = parse_multiple_urls(urls_input)
        if not urls:
            self.show_error("No se encontraron URLs válidas de YouTube.")
            return

        output_path = self.output_entry.text.strip()
        if not output_path:
            output_path = os.path.join(os.getcwd(), 'downloads')

        audio_only = self.format_var == "audio"
        quality = self.quality_spinner.text
        # Automatic workers based on URL count
        max_workers = min(len(urls), 5)  # Max 5 workers, or number of URLs if less
        if max_workers == 0:
            max_workers = 1

        self.start_button.disabled = True
        self.progress.value = 0
        self.log_message(f"Iniciando descarga de {len(urls)} URL(s) con {max_workers} worker(s) automático(s)...")

        # Run download in a separate thread
        thread = threading.Thread(target=self.run_download, args=(urls, output_path, audio_only, max_workers, quality))
        thread.start()

    def run_download(self, urls, output_path, audio_only, max_workers, quality):
        # Redirect print to log_message
        import builtins
        original_print = builtins.print

        def custom_print(*args, **kwargs):
            message = " ".join(str(arg) for arg in args)
            Clock.schedule_once(lambda dt: self._update_log(message))

        builtins.print = custom_print

        try:
            download_youtube_content(urls, output_path, max_workers=max_workers, audio_only=audio_only, quality=quality)
        except Exception as e:
            Clock.schedule_once(lambda dt: self._update_log(f"Error: {str(e)}"))
        finally:
            builtins.print = original_print
            Clock.schedule_once(lambda dt: self.download_finished())

    def download_finished(self):
        self.start_button.disabled = False
        self.progress.value = 100
        self.log_message("Descarga completada.")

    def show_error(self, message):
        popup = Popup(
            title='Error',
            content=Label(text=message),
            size_hint=(0.8, 0.4)
        )
        popup.open()

class YouTubeDownloaderApp(App):
    def build(self):
        self.title = "YouTube Downloader"
        return YouTubeDownloaderGUI()

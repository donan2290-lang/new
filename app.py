from flask import Flask, render_template, request, jsonify, Response, send_file, stream_with_context, session, g
from flask_cors import CORS
from flask_compress import Compress
from flask_babel import Babel, gettext, get_locale
import yt_dlp
import re
import os
import tempfile
import json
import time
import random
import requests
import socket
import ipaddress
from urllib.parse import urlparse
from queue import Queue
from threading import Thread
import instaloader
from fake_useragent import UserAgent
import logging

# Import configuration and utilities
from config import config, Config
from utils.logger import setup_logging
from utils.file_cleanup import cleanup_scheduler
from extensions import db
from models import DownloadTask
from services import task_service

# Initialize Flask app with config
env = os.getenv('FLASK_ENV', 'production')
app = Flask(__name__)
app.config.from_object(config[env])
Config.init_app(app)

# Setup logging
logger = setup_logging(app)

# Initialize extensions
CORS(app)
Compress(app)  # Enable gzip compression

# Initialize Babel for i18n
babel = Babel(app)

# Initialize rate limiter
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=[app.config.get('RATE_LIMIT_DEFAULT', '100 per hour')],
        storage_uri=app.config.get('RATE_LIMIT_STORAGE_URL', 'memory://'),
        enabled=app.config.get('RATE_LIMIT_ENABLED', True)
    )
    logger.info("✓ Rate limiter initialized")
except ImportError:
    limiter = None
    logger.warning("⚠️  Flask-Limiter not available - rate limiting disabled")

# Initialize file cleanup scheduler
cleanup_scheduler.init_app(app)
logger.info("✓ File cleanup scheduler initialized")

# Initialize database
db.init_app(app)
with app.app_context():
    db.create_all()
cleanup_scheduler.enable_task_tracking(True)

# Babel locale selector
def get_locale():
    """Get user's preferred language"""
    # Try to get from session
    if 'language' in session:
        return session['language']
    # Try to get from request args
    lang = request.args.get('lang')
    if lang in app.config['SUPPORTED_LANGUAGES']:
        return lang
    # Try to get from browser
    return request.accept_languages.best_match(app.config['SUPPORTED_LANGUAGES'])

babel.init_app(app, locale_selector=get_locale)

# Register Blueprints for PDF and Image Controllers
try:
    from controllers.pdf_controller import pdf_bp
    from controllers.image_controller import image_bp
    app.register_blueprint(pdf_bp)
    app.register_blueprint(image_bp)
    logger.info("✓ PDF and Image controllers registered successfully")
except Exception as e:
    logger.warning(f"⚠️ Warning: Could not register PDF/Image controllers: {str(e)}")
    logger.warning("   Install required libraries: pip install -r requirements.txt")

# Store progress for each download session
download_progress = {}


def _update_progress(session_id, payload):
    """Persist progress in-memory and mirror to DB for durability."""
    download_progress[session_id] = payload
    status = payload.get('status', 'unknown')
    message = payload.get('message')
    try:
        task_service.mark_status(session_id, status, message, progress=payload)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.debug(f"Progress sync failed for {session_id}: {exc}")

# Platform configurations
# NOTE: Order matters! Check more specific patterns first
PLATFORM_CONFIGS = {
    'youtube': {
        'patterns': [r'youtube\.com', r'youtu\.be'],
        'extractors': ['youtube']
    },
    'tiktok': {
        'patterns': [r'tiktok\.com', r'vt\.tiktok\.com'],
        'extractors': ['tiktok']
    },
    'instagram': {
        'patterns': [r'instagram\.com'],
        'extractors': ['instagram']
    },
    'facebook': {
        'patterns': [r'facebook\.com', r'fb\.watch'],
        'extractors': ['facebook']
    },
    'bilibili_tv': {
        'patterns': [r'www\.bilibili\.tv', r'bilibili\.tv'],  # bilibili.tv (International) - check FIRST
        'extractors': ['generic']
    },
    'bilibili': {
        'patterns': [r'www\.bilibili\.com', r'bilibili\.com', r'bangumi\.bilibili\.com'],  # bilibili.com (China)
        'extractors': ['bilibili']
    },
    'snackvideo': {
        'patterns': [r'snackvideo\.com'],
        'extractors': ['generic']
    },
    'twitter': {
        'patterns': [r'twitter\.com', r'x\.com', r't\.co'],
        'extractors': ['twitter']
    }
}

def detect_platform(url):
    """Detect video platform from URL"""
    for platform, config in PLATFORM_CONFIGS.items():
        for pattern in config['patterns']:
            if re.search(pattern, url, re.IGNORECASE):
                return platform
    return None

def extract_instagram_shortcode(url):
    """Extract shortcode from Instagram URL"""
    patterns = [
        r'instagram\.com/p/([A-Za-z0-9_-]+)',
        r'instagram\.com/reel/([A-Za-z0-9_-]+)',
        r'instagram\.com/reels/([A-Za-z0-9_-]+)',  # Support /reels/
        r'instagram\.com/tv/([A-Za-z0-9_-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def download_instagram_video(url):
    """Download Instagram video using Instaloader with anti-detection (without login)"""
    try:
        shortcode = extract_instagram_shortcode(url)
        if not shortcode:
            print(f"Failed to extract shortcode from URL: {url}")
            return None
        
        print(f"Instagram shortcode extracted: {shortcode}")
        
        # Generate random User-Agent to bypass detection
        ua = UserAgent()
        random_ua = ua.random
        print(f"Using User-Agent: {random_ua[:50]}...")
        
        # Random delay to mimic human behavior (2-5 seconds)
        delay = random.uniform(2, 5)
        print(f"Anti-detection delay: {delay:.2f}s")
        time.sleep(delay)
        
        # Create Instaloader instance with custom User-Agent
        loader = instaloader.Instaloader(
            download_videos=True,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            post_metadata_txt_pattern='',
            quiet=True,
            user_agent=random_ua
        )
        
        # Get post from shortcode
        print(f"Fetching Instagram post...")
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        
        # Check if it's a video
        if not post.is_video:
            print(f"Post is not a video")
            return None
        
        print(f"Video found! Owner: @{post.owner_username}")
        
        # Get video URL
        video_url = post.video_url
        
        # Get video filesize via HEAD request
        filesize_str = 'Unknown size'
        try:
            print(f"Fetching video filesize...")
            response = requests.head(video_url, timeout=5, headers={
                'User-Agent': random_ua,
                'Referer': 'https://www.instagram.com/'
            })
            if response.status_code == 200 and 'Content-Length' in response.headers:
                filesize_bytes = int(response.headers['Content-Length'])
                filesize_str = format_filesize(filesize_bytes)
                print(f"Video size: {filesize_str}")
            else:
                print(f"Could not determine filesize (status: {response.status_code})")
        except Exception as e:
            print(f"Failed to fetch filesize: {str(e)}")
        
        # Get post info
        result = {
            'success': True,
            'title': post.title or f"Instagram_{shortcode}",
            'thumbnail': post.url,
            'duration': None,
            'uploader': post.owner_username,
            'video_url': video_url,
            'formats': [{
                'quality': 'Best Quality',
                'type': 'Video + Audio',
                'resolution': 'Auto',
                'ext': 'MP4',
                'filesize': filesize_str,
                'url': video_url,
                'format_id': 'best',
                'height': 1080
            }]
        }
        
        return result
        
    except Exception as e:
        print(f"Instagram Instaloader error: {str(e)}")
        return None

def format_filesize(bytes_size):
    """Convert bytes to human readable format"""
    if not bytes_size:
        return "Unknown size"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"

def format_duration(seconds):
    """Convert seconds to readable duration"""
    if not seconds:
        return None
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"

def extract_bilibili_tv_info(url):
    """Extract video information from Bilibili.tv (International)"""
    try:
        print(f"\n=== Extracting Bilibili.tv info ===")
        print(f"URL: {url}")
        
        # Extract video ID from URL
        video_id_match = re.search(r'bilibili\.tv/(?:\w+/)?video/(\d+)', url)
        if not video_id_match:
            print("Failed to extract video ID from URL")
            return None
        
        video_id = video_id_match.group(1)
        print(f"Video ID: {video_id}")
        
        # Fetch webpage to get video info
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.bilibili.tv/',
            'Origin': 'https://www.bilibili.tv',
            'Accept-Language': 'en-US,en;q=0.9'
        }
        
        page_response = requests.get(url, headers=headers, timeout=10)
        page_response.raise_for_status()
        
        # Extract __INITIAL_STATE__
        state_match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', page_response.text, re.DOTALL)
        if not state_match:
            print("Cannot extract __INITIAL_STATE__ from page")
            return None
        
        state = json.loads(state_match.group(1))
        print("State extracted successfully")
        
        # Get video data (could be OgvVideo or UgcVideo)
        video_data = state.get('OgvVideo') or state.get('UgcVideo')
        if not video_data:
            print("Cannot find video data in page state")
            return None
        
        title = video_data.get('title') or f'Bilibili.tv Video {video_id}'
        print(f"Title: {title}")
        
        # Get thumbnail - try multiple fields
        thumbnail = None
        thumbnail_fields = ['cover', 'ogv_img', 'horizontalCover', 'horizontal_cover', 'pic', 'square_cover']
        for field in thumbnail_fields:
            if video_data.get(field):
                thumbnail = video_data.get(field)
                print(f"✓ Thumbnail found in field '{field}': {thumbnail[:100]}...")
                break
        
        if not thumbnail:
            print("⚠️ No thumbnail found in video_data")
            print(f"Available fields: {list(video_data.keys())}")
        
        # Quality mapping
        quality_labels = {
            16: '360P',
            32: '480P', 
            64: '720P (HD)',
            74: '720P 60FPS',
            80: '1080P (Full HD)',
            112: '1080P+ (High Bitrate)',
            116: '1080P 60FPS',
            120: '4K (2160P)',
            125: 'HDR',
            127: '8K'
        }
        
        formats_list = []
        tried_qualities = set()
        
        # Try UGC API first (for user uploaded videos)
        print("\n--- Trying UGC API ---")
        api_url = f'https://api.bilibili.tv/intl/gateway/web/playurl?aid={video_id}&platform=web&qn=0'
        print(f"Getting available qualities: {api_url}")
        
        try:
            api_response = requests.get(api_url, headers=headers, timeout=10)
            api_data = api_response.json()
            
            print(f"API Response code: {api_data.get('code')}")
            
            if api_data.get('code') == 0 and api_data.get('data'):
                playurl = api_data['data']
                
                # Get list of available qualities
                available_qualities = playurl.get('accept_quality', [])
                print(f"Available qualities: {available_qualities}")
                
                # Try each available quality
                for quality in available_qualities:
                    if quality in tried_qualities:
                        continue
                    tried_qualities.add(quality)
                    
                    try:
                        quality_api_url = f'https://api.bilibili.tv/intl/gateway/web/playurl?aid={video_id}&platform=web&qn={quality}'
                        print(f"  Fetching quality {quality} ({quality_labels.get(quality, str(quality))})...")
                        
                        quality_response = requests.get(quality_api_url, headers=headers, timeout=10)
                        quality_data = quality_response.json()
                        
                        if quality_data.get('code') == 0 and quality_data.get('data'):
                            qdata = quality_data['data']
                            
                            # Check durl (direct URLs)
                            if qdata.get('durl') and len(qdata['durl']) > 0:
                                video_url = qdata['durl'][0].get('url')
                                filesize = qdata['durl'][0].get('size', 0)
                                
                                if video_url:
                                    formats_list.append({
                                        'quality': f'MP4 {quality_labels.get(quality, f"{quality}P")}',
                                        'type': 'Video + Audio',
                                        'resolution': quality_labels.get(quality, f'{quality}P'),
                                        'ext': 'MP4',
                                        'filesize': format_filesize(filesize) if filesize else 'Unknown size',
                                        'url': video_url,
                                        'format_id': f'bilibili_tv_ugc_{quality}',
                                        'height': quality
                                    })
                                    print(f"    ✓ Added: {quality_labels.get(quality, f'{quality}P')}")
                            
                            # Check dash (DASH streaming)
                            elif qdata.get('dash') and qdata['dash'].get('video'):
                                dash_videos = qdata['dash']['video']
                                for dash_video in dash_videos:
                                    video_url = dash_video.get('base_url') or (dash_video.get('backup_url') or [None])[0]
                                    filesize = dash_video.get('size', 0)
                                    vid_quality = dash_video.get('id', quality)
                                    
                                    if video_url and vid_quality not in [f['height'] for f in formats_list]:
                                        formats_list.append({
                                            'quality': f'MP4 {quality_labels.get(vid_quality, f"{vid_quality}P")}',
                                            'type': 'Video + Audio',
                                            'resolution': quality_labels.get(vid_quality, f'{vid_quality}P'),
                                            'ext': 'MP4',
                                            'filesize': format_filesize(filesize) if filesize else 'Unknown size',
                                            'url': video_url,
                                            'format_id': f'bilibili_tv_dash_{vid_quality}',
                                            'height': vid_quality
                                        })
                                        print(f"    ✓ Added (DASH): {quality_labels.get(vid_quality, f'{vid_quality}P')}")
                    
                    except Exception as e:
                        print(f"    ✗ Failed quality {quality}: {str(e)}")
                        continue
        
        except Exception as e:
            print(f"UGC API error: {str(e)}")
        
        # Try OGV API if no formats found (for official/licensed content)
        if not formats_list:
            print("\n--- Trying OGV API ---")
            ogv_qualities = [64, 80, 112, 116, 120]
            
            for quality in ogv_qualities:
                if quality in tried_qualities:
                    continue
                tried_qualities.add(quality)
                
                try:
                    api_url = f'https://api.bilibili.tv/intl/gateway/web/v2/ogv/playurl?ep_id={video_id}&platform=web&qn={quality}'
                    print(f"  Trying OGV quality {quality}...")
                    
                    api_response = requests.get(api_url, headers=headers, timeout=10)
                    api_data = api_response.json()
                    
                    if api_data.get('code') == 0 and api_data.get('data'):
                        playurl_data = api_data['data'].get('playurl')
                        if playurl_data and playurl_data.get('video'):
                            for video_item in playurl_data['video']:
                                video_resource = video_item.get('video_resource')
                                if video_resource:
                                    video_url = video_resource.get('url')
                                    filesize = video_resource.get('size', 0)
                                    vid_quality = video_resource.get('quality', quality)
                                    
                                    if video_url and vid_quality not in [f['height'] for f in formats_list]:
                                        formats_list.append({
                                            'quality': f'MP4 {quality_labels.get(vid_quality, f"{vid_quality}P")}',
                                            'type': 'Video + Audio',
                                            'resolution': quality_labels.get(vid_quality, f'{vid_quality}P'),
                                            'ext': 'MP4',
                                            'filesize': format_filesize(filesize) if filesize else 'Unknown size',
                                            'url': video_url,
                                            'format_id': f'bilibili_tv_ogv_{vid_quality}',
                                            'height': vid_quality
                                        })
                                        print(f"    ✓ Added (OGV): {quality_labels.get(vid_quality, f'{vid_quality}P')}")
                
                except Exception as e:
                    print(f"    ✗ OGV quality {quality} failed: {str(e)}")
                    continue
        
        if not formats_list:
            print("❌ No formats found from any API")
            return None
        
        # Remove duplicates and sort by quality (descending)
        seen = set()
        unique_formats = []
        for fmt in formats_list:
            key = fmt['height']
            if key not in seen:
                seen.add(key)
                unique_formats.append(fmt)
        
        unique_formats.sort(key=lambda x: x.get('height', 0), reverse=True)
        
        result = {
            'success': True,
            'title': title,
            'thumbnail': thumbnail,
            'duration': None,
            'uploader': video_data.get('author') or video_data.get('up_info', {}).get('uname') or 'Bilibili.tv',
            'formats': unique_formats
        }
        
        print(f"\n✅ Successfully extracted {len(unique_formats)} unique formats")
        print(f"Thumbnail: {thumbnail[:100] if thumbnail else 'None'}...")
        return result
        
    except Exception as e:
        print(f"❌ Bilibili.tv extraction error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def extract_video_info(url, platform):
    """Extract video information using yt-dlp or RapidAPI"""
    try:
        # Special handling for Bilibili.tv
        if platform == 'bilibili_tv':
            print(f"Trying Bilibili.tv custom extractor...")
            result = extract_bilibili_tv_info(url)
            if result:
                print(f"Bilibili.tv custom extractor success!")
                return result
            print(f"Bilibili.tv custom extractor failed, trying yt-dlp...")
        
        # Special handling for Twitter/X
        if platform == 'twitter':
            print(f"Using Twitter/X downloader...")
            # Twitter/X works well with yt-dlp, just pass through
        
        # Special handling for Instagram using Instaloader
        if platform == 'instagram':
            print(f"Trying Instagram with Instaloader...")
            result = download_instagram_video(url)
            if result:
                print(f"Instagram Instaloader success!")
                return result
            print(f"Instagram Instaloader failed, trying yt-dlp...")
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best',
            'nocheckcertificate': True,
            'merge_output_format': 'mp4',
        }
        
        # Platform-specific options
        if platform == 'twitter':
            ydl_opts.update({
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
                },
            })
        elif platform == 'tiktok':
            ydl_opts.update({
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Referer': 'https://www.tiktok.com/',
                },
            })
        elif platform == 'instagram':
            ydl_opts.update({
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                },
            })
        elif platform == 'facebook':
            ydl_opts.update({
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                },
            })
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if not info:
                return None
            
            # Extract basic information
            result = {
                'success': True,
                'title': info.get('title', 'Unknown Title'),
                'thumbnail': info.get('thumbnail'),
                'duration': format_duration(info.get('duration')),
                'uploader': info.get('uploader'),
                'original_url': url,  # Store original URL
                'formats': []
            }
            
            # Extract available formats
            formats = info.get('formats', [])
            
            # DEBUG: Print what formats we got
            print(f"\n=== DEBUG: Formats from yt-dlp ({platform}) ===")
            print(f"Total formats found: {len(formats)}")
            if formats:
                for fmt in formats[:3]:  # Show first 3 formats as example
                    print(f"  Format {fmt.get('format_id')}: {fmt.get('ext')} - vcodec:{fmt.get('vcodec')} acodec:{fmt.get('acodec')} height:{fmt.get('height')} protocol:{fmt.get('protocol')}")
            
            # Separate video and audio formats
            video_formats = []
            audio_formats = []
            seen_formats = set()
            
            # Get best audio format for merging with video-only
            best_audio = None
            for fmt in formats:
                acodec = fmt.get('acodec', 'none')
                vcodec = fmt.get('vcodec', 'none')
                if vcodec == 'none' and acodec != 'none':
                    if not best_audio or fmt.get('abr', 0) > best_audio.get('abr', 0):
                        best_audio = fmt
            
            for fmt in formats:
                url_download = fmt.get('url')
                if not url_download:
                    continue
                
                # Skip HLS/DASH streaming formats
                protocol = fmt.get('protocol', '')
                if 'hls' in protocol.lower() or 'm3u8' in url_download.lower() or 'manifest' in url_download.lower():
                    continue
                
                ext = fmt.get('ext', 'mp4')
                vcodec = fmt.get('vcodec', 'none')
                acodec = fmt.get('acodec', 'none')
                height = fmt.get('height')
                width = fmt.get('width', 0)
                abr = fmt.get('abr', 0)
                filesize = fmt.get('filesize') or fmt.get('filesize_approx')
                format_id = fmt.get('format_id', '')
                
                # If filesize not available, try to fetch from HEAD request
                if not filesize and url_download:
                    try:
                        head_response = requests.head(url_download, timeout=3, allow_redirects=True)
                        if head_response.status_code == 200 and 'Content-Length' in head_response.headers:
                            filesize = int(head_response.headers['Content-Length'])
                            print(f"Fetched filesize for {format_id}: {format_filesize(filesize)}")
                    except Exception as e:
                        print(f"Failed to fetch filesize for {format_id}: {str(e)}")
                
                # Video with audio (already combined)
                # Twitter: http-* formats have built-in audio even if acodec is 'none'
                is_twitter_http = platform == 'twitter' and format_id.startswith('http-')
                
                if (vcodec != 'none' and acodec != 'none' and height) or (is_twitter_http and height):
                    # Convert height to standard resolution labels
                    if height >= 2160:
                        res_label = '2160p (4K)'
                    elif height >= 1440:
                        res_label = '1440p (2K)'
                    elif height >= 1080:
                        res_label = '1080p (Full HD)'
                    elif height >= 720:
                        res_label = '720p (HD)'
                    elif height >= 480:
                        res_label = '480p'
                    else:
                        res_label = f'{height}p'
                    
                    quality_label = f"{ext.upper()} {res_label}"
                    
                    if quality_label in seen_formats:
                        continue
                    seen_formats.add(quality_label)
                    
                    video_formats.append({
                        'quality': quality_label,
                        'type': 'Video + Audio',
                        'resolution': f"{width}x{height}",
                        'ext': ext.upper(),
                        'filesize': format_filesize(filesize) if filesize else "Unknown size",
                        'url': url_download,
                        'format_id': format_id,
                        'height': height
                    })
                
                # Video-only (need to merge with audio) - YouTube style
                elif vcodec != 'none' and acodec == 'none' and height and best_audio:
                    # Only include good quality video-only formats
                    if height >= 720:  # Skip low quality video-only
                        # Convert height to standard resolution labels
                        if height >= 2160:
                            res_label = '2160p (4K)'
                        elif height >= 1440:
                            res_label = '1440p (2K)'
                        elif height >= 1080:
                            res_label = '1080p (Full HD)'
                        elif height >= 720:
                            res_label = '720p (HD)'
                        else:
                            res_label = f'{height}p'
                        
                        quality_label = f"{ext.upper()} {res_label}"
                        
                        if quality_label in seen_formats:
                            continue
                        seen_formats.add(quality_label)
                        
                        # Estimate combined size
                        audio_size = best_audio.get('filesize') or best_audio.get('filesize_approx') or 0
                        combined_size = (filesize or 0) + audio_size
                        
                        # Use special format_id that includes audio
                        combined_format_id = f"{format_id}+{best_audio.get('format_id')}"
                        
                        video_formats.append({
                            'quality': quality_label,
                            'type': 'Video + Audio',
                            'resolution': f"{width}x{height}",
                            'ext': ext.upper(),
                            'filesize': format_filesize(combined_size) if combined_size else "Unknown size",
                            'url': url_download,
                            'format_id': combined_format_id,
                            'height': height
                        })
                
                # Audio only
                elif vcodec == 'none' and acodec != 'none':
                    audio_codec = acodec.split('.')[0].upper()
                    bitrate = int(abr) if abr else 0
                    quality_label = f"Audio {audio_codec}{bitrate}"
                    
                    if quality_label in seen_formats:
                        continue
                    seen_formats.add(quality_label)
                    
                    audio_formats.append({
                        'quality': quality_label,
                        'type': 'Audio Only',
                        'resolution': f"{bitrate}kbps" if bitrate else "Unknown",
                        'ext': ext.upper(),
                        'filesize': format_filesize(filesize) if filesize else "Unknown size",
                        'url': url_download,
                        'format_id': format_id,
                        'bitrate': bitrate
                    })
            
            # Sort video formats by height (descending)
            video_formats.sort(key=lambda x: x.get('height', 0), reverse=True)
            
            # Sort audio formats by bitrate (descending)
            audio_formats.sort(key=lambda x: x.get('bitrate', 0), reverse=True)
            
            # Combine: videos first, then audio
            result['formats'] = video_formats + audio_formats
            
            # DEBUG: Show final result
            print(f"=== DEBUG: Final result for {platform} ===")
            print(f"Video formats: {len(video_formats)}, Audio formats: {len(audio_formats)}")
            print(f"Total formats returned: {len(result['formats'])}")
            
            # FALLBACK: If no formats found, add generic format from the best available
            if not result['formats'] and formats:
                print("⚠️ No formats passed filter - adding fallback generic format")
                best_format = formats[-1]  # Usually the last one is the best
                url_download = best_format.get('url')
                if url_download:
                    filesize = best_format.get('filesize') or best_format.get('filesize_approx')
                    if not filesize:
                        try:
                            head_response = requests.head(url_download, timeout=3, allow_redirects=True)
                            if head_response.status_code == 200 and 'Content-Length' in head_response.headers:
                                filesize = int(head_response.headers['Content-Length'])
                        except:
                            pass
                    
                    result['formats'].append({
                        'quality': f"{best_format.get('ext', 'mp4').upper()} Best Quality",
                        'type': 'Video + Audio',
                        'resolution': 'Unknown',
                        'ext': best_format.get('ext', 'mp4').upper(),
                        'filesize': format_filesize(filesize) if filesize else "Unknown size",
                        'url': url_download,
                        'format_id': best_format.get('format_id', 'best'),
                        'height': 0
                    })
                    print(f"✅ Added fallback format: {result['formats'][0]['quality']}")
            
            if result['formats']:
                print(f"First format: {result['formats'][0]}")
            else:
                print("❌ ERROR: Still no formats available!")
            
            return result
            
    except Exception as e:
        error_msg = str(e)
        print(f"Error extracting video info: {error_msg}")
        
        # Provide helpful error messages
        if 'IP address is blocked' in error_msg or 'blocked from accessing' in error_msg:
            return {
                'success': False,
                'error': f'{platform.capitalize()} has blocked access from your region/IP address. Try using a VPN or different network.',
                'error_type': 'geo_blocked'
            }
        
        return None

# -------------------- Security helpers --------------------
def _host_is_private(host: str) -> bool:
    try:
        # Remove port if present
        hostname = host.split(':', 1)[0]
        ip = ipaddress.ip_address(socket.gethostbyname(hostname))
        return ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local
    except Exception:
        return False

def is_safe_public_url(raw_url: str, allow_hosts=None) -> bool:
    try:
        u = urlparse(raw_url)
        if u.scheme not in ('http', 'https'):
            return False
        if not u.netloc:
            return False
        if _host_is_private(u.netloc):
            return False
        if allow_hosts:
            host = u.hostname or ''
            return any(host.endswith(allowed) for allowed in allow_hosts)
        return True
    except Exception:
        return False

@app.before_request
def before_request():
    """Log incoming requests"""
    g.start_time = time.time()
    logger.debug(f"{request.method} {request.path} from {request.remote_addr}")

@app.after_request
def after_request(resp: Response):
    """Add security headers and log response"""
    # Security headers
    resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
    resp.headers.setdefault('X-Frame-Options', 'DENY')
    resp.headers.setdefault('Referrer-Policy', 'no-referrer-when-downgrade')
    resp.headers.setdefault('Permissions-Policy', 'geolocation=(), microphone=(), camera=()')
    csp = (
        "default-src 'self'; "
        "img-src 'self' data: https: blob:; "
        "script-src 'self' 'unsafe-inline' blob:; "
        "style-src 'self' 'unsafe-inline'; "
        "connect-src 'self' blob:; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    resp.headers.setdefault('Content-Security-Policy', csp)
    
    # Add caching headers for static assets
    if request.path.startswith('/static/'):
        resp.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    elif request.path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico', '.webp')):
        resp.headers['Cache-Control'] = 'public, max-age=31536000'
    elif resp.content_type and 'text/html' in resp.content_type:
        resp.headers['Cache-Control'] = 'no-cache, must-revalidate'
    
    # Log response time
    if hasattr(g, 'start_time'):
        duration = time.time() - g.start_time
        logger.info(f"{request.method} {request.path} - {resp.status_code} - {duration:.3f}s")
    
    return resp

@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded"""
    logger.warning(f"Rate limit exceeded from {request.remote_addr}")
    return jsonify({
        'success': False,
        'error': gettext('rate_limit_exceeded')
    }), 429

@app.errorhandler(500)
def internal_error(error):
    """Handle internal server error"""
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({
        'success': False,
        'error': gettext('server_error')
    }), 500

# Language switching endpoint
@app.route('/set-language/<lang>')
def set_language(lang):
    """Set user's preferred language"""
    if lang in app.config['SUPPORTED_LANGUAGES']:
        session['language'] = lang
        logger.info(f"Language set to: {lang} for {request.remote_addr}")
    return jsonify({'success': True, 'language': lang})

# Health check endpoint
@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    stats = cleanup_scheduler.get_folder_stats()
    return jsonify({
        'status': 'healthy',
        'version': '1.0.0',
        'environment': app.config['ENV'],
        'storage': stats
    })

@app.route('/')
def index():
    return render_template('index.html', platform='all', title='Snapload - Download Video YouTube, TikTok, Instagram & More')

@app.route('/youtube')
def youtube_page():
    return render_template('index.html', 
                         platform='youtube',
                         title='Snapload YouTube Downloader - Download Video YouTube',
                         description='Download video YouTube kualitas HD. Support 1080p, 720p, 480p, dan format audio MP3.')

@app.route('/tiktok')
def tiktok_page():
    return render_template('index.html',
                         platform='tiktok',
                         title='Snapload TikTok Downloader - Download TikTok Tanpa Watermark',
                         description='Download video TikTok tanpa watermark. Download TikTok cepat dan mudah.')

@app.route('/instagram')
def instagram_page():
    return render_template('index.html',
                         platform='instagram',
                         title='Snapload Instagram Downloader - Download Instagram Reels & Video',
                         description='Download video Instagram, reels, dan IGTV. Download Instagram kualitas tinggi.')

@app.route('/facebook')
def facebook_page():
    return render_template('index.html',
                         platform='facebook',
                         title='Snapload Facebook Downloader - Download Video Facebook',
                         description='Download video Facebook kualitas HD. Download Facebook cepat dan mudah.')

@app.route('/bilibili')
def bilibili_page():
    return render_template('index.html',
                         platform='bilibili',
                         title='Snapload BStation Downloader - Download Video BStation',
                         description='Download video dari BStation (Bilibili.com & Bilibili.tv). Support berbagai pilihan kualitas.')

@app.route('/bilibili-tv')
def bilibili_tv_page():
    return render_template('index.html',
                         platform='bilibili_tv',
                         title='Snapload BStation.tv Downloader - Download Video BStation',
                         description='Download video dari BStation.tv (Bilibili International). Support 720P, 1080P, 1080P+ quality.')

@app.route('/snackvideo')
def snackvideo_page():
    return render_template('index.html',
                         platform='snackvideo',
                         title='Snapload Snack Video Downloader - Download Snack Video',
                         description='Download konten Snack Video dengan mudah. Download Snack Video cepat.')

@app.route('/twitter')
def twitter_page():
    return render_template('index.html',
                         platform='twitter',
                         title='Snapload Twitter/X Downloader - Download Twitter/X Videos',
                         description='Download video dari Twitter/X dengan mudah. Support HD quality dan GIF.')

@app.route('/pdf-converter')
@app.route('/pdf-converter/<tool_type>')
def pdf_converter_page(tool_type=None):
    return render_template('pdf_converter.html',
                         tool_type=tool_type,
                         title='PDF Converter - Convert PDF to Word, JPG, PNG & More',
                         description='Free online PDF converter. Convert PDF to Word, Excel, JPG, PNG and more.')

@app.route('/image-converter')
@app.route('/image-converter/<tool_type>')
def image_converter_page(tool_type=None):
    return render_template('image_converter.html',
                         tool_type=tool_type,
                         title='Image Converter - Convert JPG, PNG, WebP & More',
                         description='Free online image converter. Convert JPG to PNG, WebP to JPG and more.')

@app.route('/api/get-download-url', methods=['POST'])
def get_download_url():
    """Get direct download URL - return proxy URL instead of direct URL"""
    try:
        data = request.get_json()
        video_url = data.get('video_url')
        format_id = data.get('format_id')
        platform = data.get('platform')
        direct_url = data.get('direct_url')
        filename = data.get('filename', 'video.mp4')
        
        print(f"\n=== Get Download URL (Proxy Mode) ===")
        print(f"Video URL: {video_url}")
        print(f"Format ID: {format_id}")
        print(f"Platform: {platform}")
        
        # Create a download session ID
        session_id = str(int(time.time() * 1000))
        
        # Store download info in temporary dict (you might want to use Redis in production)
        if not hasattr(get_download_url, 'pending_downloads'):
            get_download_url.pending_downloads = {}
        
        get_download_url.pending_downloads[session_id] = {
            'video_url': video_url,
            'direct_url': direct_url,
            'format_id': format_id,
            'filename': filename,
            'platform': platform
        }

        # Persist session metadata for cleanup/observability
        try:
            task_service.upsert_task(session_id, defaults={
                'platform': platform,
                'source_url': video_url,
                'direct_url': direct_url,
                'requested_filename': filename,
                'status': 'pending',
                'message': 'Waiting for download request'
            })
        except Exception as exc:
            logger.debug(f"Task tracking init failed for {session_id}: {exc}")
        
        # Return proxy URL that will force download
        proxy_url = f"/api/force-download/{session_id}"
        
        print(f"✅ Proxy download URL created: {proxy_url}")
        
        return jsonify({
            'success': True,
            'download_url': proxy_url
        })
        
    except Exception as e:
        print(f"❌ Error getting download URL: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/force-download/<session_id>')
def force_download(session_id):
    """Force browser to download video with proper headers"""
    try:
        # Get download info
        if not hasattr(get_download_url, 'pending_downloads'):
            return "Download session expired", 404
        
        download_info = get_download_url.pending_downloads.get(session_id)
        if not download_info:
            return "Download session not found", 404
        
        video_url = download_info['video_url']
        direct_url = download_info['direct_url']
        format_id = download_info['format_id']
        filename = download_info['filename']
        platform = download_info['platform']
        
        print(f"\n=== Force Download Session: {session_id} ===")
        print(f"Filename: {filename}")
        print(f"Platform: {platform}")
        
        # SPECIAL: For Bilibili.tv, refresh URL first
        if platform == 'bilibili_tv' and video_url:
            print("🔄 Refreshing Bilibili.tv URL (URLs expire quickly)...")
            
            # Re-extract to get fresh URL
            fresh_info = extract_bilibili_tv_info(video_url)
            if fresh_info and fresh_info.get('formats'):
                # Find matching format by format_id
                for fmt in fresh_info['formats']:
                    if fmt['format_id'] == format_id:
                        direct_url = fmt['url']
                        print(f"✅ Got fresh URL for {format_id}")
                        break
                else:
                    # If exact format not found, use first format
                    direct_url = fresh_info['formats'][0]['url']
                    print(f"⚠️ Format {format_id} not found, using first available")
            else:
                print("❌ Failed to refresh URL, using original (may fail)")
        
        # If direct URL provided (Instagram, Snack Video, Bilibili.tv), use it
        if direct_url and direct_url.startswith('http'):
            # Validate direct URL to prevent SSRF
            if not is_safe_public_url(direct_url):
                return "Invalid or unsafe download URL", 400
            print(f"Using direct URL for streaming")
            
            # Sanitize filename for HTTP header (remove emojis and special characters)
            import re
            safe_filename = re.sub(r'[^\x00-\x7F]+', '', filename)  # Remove non-ASCII
            safe_filename = re.sub(r'[<>:"/\\|?*]', '', safe_filename)  # Remove invalid chars
            safe_filename = safe_filename.strip() or 'video.mp4'  # Fallback if empty
            print(f"Sanitized filename: {safe_filename}")
            
            # Add platform-specific headers
            download_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            if platform == 'bilibili_tv':
                download_headers['Referer'] = 'https://www.bilibili.tv/'
                download_headers['Origin'] = 'https://www.bilibili.tv'
                print("Added Bilibili.tv headers")
            
            # Stream from direct URL with download headers
            response = requests.get(direct_url, stream=True, headers=download_headers, timeout=30, allow_redirects=True)
            # Optional: enforce max size
            max_bytes = int(os.getenv('MAX_DOWNLOAD_SIZE_MB', '500')) * 1024 * 1024
            try:
                cl = int(response.headers.get('content-length', '0'))
                if cl and cl > max_bytes:
                    return f"File too large (> {max_bytes // (1024*1024)} MB)", 413
            except Exception:
                pass
            
            if response.status_code != 200:
                print(f"❌ Failed to fetch video: HTTP {response.status_code}")
                return f"Failed to download video: HTTP {response.status_code}", response.status_code
            
            def generate():
                try:
                    for chunk in response.iter_content(chunk_size=1024*1024):
                        if chunk:
                            yield chunk
                except Exception as e:
                    print(f"❌ Streaming error: {e}")
            
            # Clean up session
            del get_download_url.pending_downloads[session_id]
            
            return Response(
                generate(),
                headers={
                    'Content-Type': 'video/mp4',
                    'Content-Disposition': f'attachment; filename="{safe_filename}"',
                    'Content-Length': response.headers.get('content-length', ''),
                    'Accept-Ranges': 'bytes'
                }
            )
        
        # Otherwise use yt-dlp to download and stream
        print(f"Using yt-dlp for download")
        
        temp_dir = tempfile.mkdtemp()
        temp_file = os.path.join(temp_dir, filename)
        
        ydl_opts = {
            'format': format_id if format_id else 'best',
            'outtmpl': temp_file,
            'quiet': False,
            'no_warnings': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        # Find the downloaded file
        downloaded_file = None
        for f in os.listdir(temp_dir):
            if f.startswith(os.path.splitext(filename)[0]):
                downloaded_file = os.path.join(temp_dir, f)
                break
        
        if not downloaded_file or not os.path.exists(downloaded_file):
            return "Download failed", 500
        
        print(f"✅ File ready: {downloaded_file}")
        
        # Stream file with download headers
        def generate():
            with open(downloaded_file, 'rb') as f:
                while True:
                    chunk = f.read(1024*1024)
                    if not chunk:
                        break
                    yield chunk
            # Cleanup after streaming
            try:
                os.remove(downloaded_file)
                os.rmdir(temp_dir)
            except:
                pass
        
        # Clean up session
        del get_download_url.pending_downloads[session_id]
        
        file_size = os.path.getsize(downloaded_file)
        
        return Response(
            generate(),
            headers={
                'Content-Type': 'video/mp4',
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Length': str(file_size),
                'Accept-Ranges': 'bytes'
            }
        )
        
    except Exception as e:
        print(f"❌ Force download error: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Download error: {str(e)}", 500

@app.route('/api/download', methods=['POST'])
def download():
    """Handle download requests"""
    if limiter:
        limiter.limit(app.config.get('RATE_LIMIT_DOWNLOAD', '10 per hour'))(lambda: None)()
    
    try:
        data = request.get_json()
        url = data.get('url')
        platform = data.get('platform')
        
        if not url:
            return jsonify({
                'success': False,
                'error': 'URL is required'
            }), 400
        
        # Auto-detect platform if not provided
        if not platform:
            platform = detect_platform(url)
        
        if not platform:
            return jsonify({
                'success': False,
                'error': 'Unsupported platform'
            }), 400
        
        # Extract video information
        video_info = extract_video_info(url, platform)
        
        if not video_info:
            return jsonify({
                'success': False,
                'error': 'Failed to extract video information. Please check the URL and try again.'
            }), 500
        
        # Check if extraction returned an error
        if isinstance(video_info, dict) and video_info.get('success') == False:
            return jsonify(video_info), 400
        
        return jsonify(video_info)
        
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@app.route('/api/proxy-download', methods=['POST', 'GET'])
def proxy_download():
    """Download video using yt-dlp and stream to client"""
    try:
        # Support both POST (old) and GET (new direct Chrome download)
        if request.method == 'GET':
            video_url = request.args.get('video_url')
            direct_url = request.args.get('direct_url')
            format_id = request.args.get('format_id')
            filename = request.args.get('filename', 'video.mp4')
            session_id = request.args.get('session_id', str(time.time()))
            platform = request.args.get('platform', '')
        else:
            data = request.get_json()
            video_url = data.get('video_url')  # Original video page URL
            direct_url = data.get('direct_url')  # Direct video URL (for Instagram)
            format_id = data.get('format_id')
            filename = data.get('filename', 'video.mp4')
            session_id = data.get('session_id', str(time.time()))
            platform = data.get('platform', '')
        
        if not video_url and not direct_url:
            return jsonify({'error': 'Video URL is required'}), 400
        
        print(f"Downloading: {video_url or direct_url}")
        print(f"Format: {format_id}")
        print(f"Session: {session_id}")
        print(f"Platform: {platform}")

        try:
            task_service.upsert_task(session_id, defaults={
                'platform': platform,
                'source_url': video_url or direct_url,
                'direct_url': direct_url,
                'requested_filename': filename
            })
        except Exception as exc:
            logger.debug(f"Task bootstrap failed for {session_id}: {exc}")
        
        # Initialize progress tracking
        _update_progress(session_id, {
            'status': 'starting',
            'message': 'Memulai download...',
            'percent': 0
        })
        
        # For Instagram or Bilibili.tv with direct URL, download directly without yt-dlp
        if direct_url and platform in ['instagram', 'bilibili_tv']:
            # Validate direct URL to prevent SSRF
            if not is_safe_public_url(direct_url):
                return jsonify({'error': 'Invalid or unsafe direct URL'}), 400
            print(f"{platform} direct download mode")
            
            # SPECIAL: For Bilibili.tv, refresh the URL because it expires quickly
            if platform == 'bilibili_tv':
                print("🔄 Refreshing Bilibili.tv URL (URLs expire quickly)...")
                _update_progress(session_id, {
                    'status': 'extracting',
                    'message': 'Refreshing video URL...',
                    'percent': 5
                })
                
                # Re-extract to get fresh URL
                fresh_info = extract_bilibili_tv_info(video_url)
                if fresh_info and fresh_info.get('formats'):
                    # Find matching format by format_id
                    for fmt in fresh_info['formats']:
                        if fmt['format_id'] == format_id:
                            direct_url = fmt['url']
                            print(f"✅ Got fresh URL for {format_id}")
                            break
                    else:
                        # If exact format not found, use first format
                        direct_url = fresh_info['formats'][0]['url']
                        print(f"⚠️ Format {format_id} not found, using first available")
                else:
                    print("❌ Failed to refresh URL, using original (may fail)")
            
            temp_dir = tempfile.mkdtemp()
            temp_file = os.path.join(temp_dir, filename)
            task_service.register_storage(session_id, temp_file, storage_type='temp')
            
            _update_progress(session_id, {
                'status': 'downloading',
                'message': f'Downloading {platform} video...',
                'percent': 10
            })
            
            # Download using requests with streaming
            download_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            # Add platform-specific headers
            if platform == 'bilibili_tv':
                download_headers['Referer'] = 'https://www.bilibili.tv/'
                download_headers['Origin'] = 'https://www.bilibili.tv'
            
            response = requests.get(direct_url, stream=True, headers=download_headers, allow_redirects=True)
            # Optional: enforce max size
            max_bytes = int(os.getenv('MAX_DOWNLOAD_SIZE_MB', '500')) * 1024 * 1024
            try:
                cl = int(response.headers.get('content-length', '0'))
                if cl and cl > max_bytes:
                    return jsonify({'error': f'File too large (> {max_bytes // (1024*1024)} MB)'}), 413
            except Exception:
                pass
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=524288):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size:
                            percent = (downloaded / total_size) * 100
                            _update_progress(session_id, {
                                'status': 'downloading',
                                'message': 'Downloading video...',
                                'percent': round(percent, 1),
                                'downloaded': downloaded,
                                'total': total_size
                            })
            
            print(f"{platform} video downloaded: {temp_file}")
            try:
                direct_file_size = os.path.getsize(temp_file)
            except OSError:
                direct_file_size = None
            task_service.register_storage(session_id, temp_file, storage_type='temp', file_size=direct_file_size)
            
            _update_progress(session_id, {
                'status': 'streaming',
                'message': 'Mengirim file ke browser...',
                'percent': 100
            })
            
            # Stream file to client
            def generate():
                try:
                    with open(temp_file, 'rb') as f:
                        while True:
                            chunk = f.read(524288)
                            if not chunk:
                                break
                            yield chunk
                finally:
                    try:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                        if os.path.exists(temp_dir):
                            os.rmdir(temp_dir)
                    except:
                        pass
            
            return Response(
                stream_with_context(generate()),
                mimetype='video/mp4',
                headers={
                    'Content-Disposition': f'attachment; filename="{filename}"',
                    'Content-Type': 'video/mp4'
                }
            )
        
        # Standard yt-dlp download for other platforms
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        output_template = os.path.join(temp_dir, 'video.%(ext)s')
        
        # Progress hook
        def progress_hook(d):
            try:
                print(f"Progress hook: {d['status']} - {d}")
                
                if d['status'] == 'downloading':
                    # Calculate percent
                    if 'total_bytes' in d and d['total_bytes']:
                        percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
                        _update_progress(session_id, {
                            'status': 'downloading',
                            'message': 'Downloading video...',
                            'percent': round(percent, 1),
                            'downloaded': d['downloaded_bytes'],
                            'total': d['total_bytes']
                        })
                        print(f"Progress: {percent:.1f}% ({d['downloaded_bytes']}/{d['total_bytes']})")
                    elif 'total_bytes_estimate' in d and d['total_bytes_estimate']:
                        percent = (d['downloaded_bytes'] / d['total_bytes_estimate']) * 100
                        _update_progress(session_id, {
                            'status': 'downloading',
                            'message': 'Downloading video...',
                            'percent': round(percent, 1),
                            'downloaded': d['downloaded_bytes'],
                            'total': d['total_bytes_estimate']
                        })
                        print(f"Progress (estimate): {percent:.1f}%")
                    elif 'downloaded_bytes' in d:
                        _update_progress(session_id, {
                            'status': 'downloading',
                            'message': 'Downloading video...',
                            'downloaded': d['downloaded_bytes']
                        })
                        print(f"Downloaded: {d['downloaded_bytes']} bytes")
                        
                elif d['status'] == 'finished':
                    print("Download finished, processing...")
                    _update_progress(session_id, {
                        'status': 'processing',
                        'message': 'Memproses video (merging audio+video)...',
                        'percent': 95
                    })
            except Exception as e:
                print(f"Progress hook error: {e}")
        
        # yt-dlp options with optimizations for Facebook
        ydl_opts = {
            'format': format_id if format_id else 'best',
            'outtmpl': output_template,
            'quiet': False,
            'no_warnings': False,
            'verbose': True,  # Enable verbose for progress tracking
            'progress_hooks': [progress_hook],
            'noprogress': False,  # Ensure progress is shown
            'concurrent_fragment_downloads': 5,  # Faster download
            'retries': 3,
            'fragment_retries': 3,
            'http_chunk_size': 1048576,  # 1MB chunks
        }
        
        # Download video
        print(f"Starting download for session {session_id}")
        _update_progress(session_id, {
            'status': 'extracting',
            'message': 'Mengambil informasi video...',
            'percent': 5
        })
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print("Extracting video info...")
            info = ydl.extract_info(video_url, download=True)
            downloaded_file = ydl.prepare_filename(info)
            print(f"Download complete: {downloaded_file}")
        
        print(f"File downloaded successfully: {downloaded_file}")
        
        # Get file size
        file_size = os.path.getsize(downloaded_file)
        print(f"File size: {file_size} bytes ({file_size/(1024*1024):.2f} MB)")
        
        _update_progress(session_id, {
            'status': 'streaming',
            'message': 'Mengirim file ke browser...',
            'percent': 100
        })
        
        # Stream file to client with optimized buffering
        def generate():
            try:
                chunk_size = 1048576  # 1MB chunks for faster transfer
                bytes_sent = 0
                with open(downloaded_file, 'rb') as f:
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        bytes_sent += len(chunk)
                        progress_pct = (bytes_sent / file_size) * 100 if file_size > 0 else 100
                        print(f"Streaming: {progress_pct:.1f}% ({bytes_sent}/{file_size} bytes)")
                        yield chunk
                print(f"Streaming complete: {bytes_sent} bytes sent")
            finally:
                # Cleanup immediately after streaming
                try:
                    print("Cleaning up temporary files...")
                    if os.path.exists(downloaded_file):
                        os.remove(downloaded_file)
                        print(f"Removed: {downloaded_file}")
                    if os.path.exists(temp_dir):
                        os.rmdir(temp_dir)
                        print(f"Removed: {temp_dir}")
                    # Remove progress tracking to signal SSE completion
                    if session_id in download_progress:
                        del download_progress[session_id]
                        print(f"Cleared progress for session: {session_id}")
                except Exception as e:
                    print(f"Cleanup error: {e}")
        
        # Sanitize filename for HTTP header (remove emojis and special characters)
        import re
        safe_filename = re.sub(r'[^\x00-\x7F]+', '', filename)  # Remove non-ASCII
        safe_filename = re.sub(r'[<>:"/\\|?*]', '', safe_filename)  # Remove invalid chars
        safe_filename = safe_filename.strip() or 'video.mp4'  # Fallback if empty
        
        # Create response with proper streaming headers
        response = Response(stream_with_context(generate()), mimetype='video/mp4', direct_passthrough=True)
        response.headers['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
        response.headers['Content-Length'] = str(file_size)
        response.headers['Content-Type'] = 'video/mp4'
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['X-Accel-Buffering'] = 'no'
        
        print(f"Sending response with {file_size} bytes ({file_size/(1024*1024):.2f} MB)")
        return response
        
    except Exception as e:
        print(f"Download error: {str(e)}")
        import traceback
        traceback.print_exc()
        # Cleanup progress on error
        if 'session_id' in locals() and session_id in download_progress:
            del download_progress[session_id]
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

@app.route('/api/download-progress/<session_id>')
def get_download_progress(session_id):
    """SSE endpoint for streaming download progress"""
    print(f"SSE connection started for session: {session_id}")
    
    def generate():
        last_status = None
        timeout = 0
        max_timeout = 180  # 3 minutes (reduced from 5)
        no_update_count = 0
        
        while timeout < max_timeout:
            if session_id in download_progress:
                current = download_progress[session_id]
                
                # Send update if status changed
                if current != last_status:
                    print(f"SSE sending: {current}")
                    yield f"data: {json.dumps(current)}\n\n"
                    last_status = current.copy()
                    no_update_count = 0
                else:
                    no_update_count += 1
                
                # Don't close SSE immediately on streaming status
                # Let the cleanup process remove the session when done
                if current.get('status') == 'streaming':
                    # Just send the status update, don't close
                    pass
            else:
                # Session not found yet, wait
                pass
            
            time.sleep(0.3)
            timeout += 0.3
        
        # Timeout
        if timeout >= max_timeout:
            print(f"SSE connection timeout for session: {session_id}")
            yield f"data: {{\"status\": \"timeout\"}}\n\n"
    
    response = Response(stream_with_context(generate()), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    return response

@app.route('/api/proxy-image')
def proxy_image():
    """Proxy Instagram/Facebook images to bypass CORS"""
    image_url = request.args.get('url')
    
    if not image_url:
        return jsonify({'error': 'No URL provided'}), 400
    
    try:
        # Allow-list of trusted hosts
        allow_hosts = (
            'cdninstagram.com',
            'instagram.com',
            'fbcdn.net',
            'facebook.com',
        )
        if not is_safe_public_url(image_url, allow_hosts=allow_hosts):
            return jsonify({'error': 'Invalid or unsupported image host'}), 400
        # Fetch image with proper headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://www.instagram.com/',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8'
        }
        
        response = requests.get(image_url, headers=headers, timeout=10, stream=True)
        
        if response.status_code == 200:
            # Return image with proper headers
            return Response(
                response.content,
                mimetype=response.headers.get('Content-Type', 'image/jpeg'),
                headers={
                    'Cache-Control': 'public, max-age=3600',
                    'Access-Control-Allow-Origin': '*'
                }
            )
        else:
            return jsonify({'error': f'Failed to fetch image: {response.status_code}'}), 500
            
    except Exception as e:
        print(f"Image proxy error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("🚀 Snapload - Video Downloader Server Starting...")
    logger.info("=" * 60)
    logger.info("📱 Supported Platforms:")
    for platform in PLATFORM_CONFIGS.keys():
        display_name = platform.replace('_', ' ').title()
        logger.info(f"   ✓ {display_name}")
    logger.info("=" * 60)
    logger.info(f"Environment: {app.config['ENV']}")
    logger.info(f"Debug Mode: {app.config['DEBUG']}")
    logger.info(f"Rate Limiting: {'Enabled' if app.config.get('RATE_LIMIT_ENABLED') else 'Disabled'}")
    logger.info(f"Auto Cleanup: {'Enabled' if app.config.get('AUTO_CLEANUP_ENABLED') else 'Disabled'}")
    logger.info(f"Supported Languages: {', '.join(app.config['SUPPORTED_LANGUAGES'])}")
    logger.info("=" * 60)
    logger.info(f"🌐 Server running on: http://{app.config['HOST']}:{app.config['PORT']}")
    logger.info("=" * 60)
    logger.info("\nPress Ctrl+C to stop the server\n")
    
    try:
        app.run(
            debug=app.config['DEBUG'],
            host=app.config['HOST'],
            port=app.config['PORT'],
            threaded=True
        )
    except KeyboardInterrupt:
        logger.info("\n🛑 Shutting down server...")
        cleanup_scheduler.stop()
        logger.info("✓ Server stopped gracefully")


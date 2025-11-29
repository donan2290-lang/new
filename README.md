# VideoDownloaderApp

Flask-based video downloader supporting multiple platforms (YouTube, Instagram, TikTok, Facebook, Twitter) with PDF and image conversion features.

## 🎯 Features

- 📹 Multi-platform video download (YouTube, Instagram, TikTok, Facebook, Twitter)
- 🖼️ Image converter (format conversion, resize, compress, background removal)
- 📄 PDF converter (PDF ↔ Word, Excel, Image, etc.)
- 🗄️ SQLite database for download tracking
- 🧹 Auto-cleanup expired files (configurable retention)
- 🌐 Multi-language support (Indonesian/English)
- ⚡ Rate limiting & security features
- 📊 Real-time progress tracking

## 🚀 Quick Start

### Local Development

```bash
# Clone repository
git clone https://github.com/yourusername/VideoDownloaderApp.git
cd VideoDownloaderApp

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# or: source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Initialize database
python init_db.py

# Run application
python app.py
```

Visit: http://localhost:5000

### Deploy to Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template)

See `DEPLOY_RAILWAY.md` for detailed deployment instructions.

## 🔧 Configuration

Create `.env` file:

```env
FLASK_ENV=production
SECRET_KEY=your-super-secret-key
DATABASE_URL=sqlite:///snapload.db
DOWNLOAD_RETENTION_HOURS=24
RATE_LIMIT_ENABLED=True
AUTO_CLEANUP_ENABLED=True
```

## 📚 Documentation

- `DEPLOY_RAILWAY.md` - Railway deployment guide (3 methods)
- `DEPLOY_HOSTINGER.md` - Hostinger/VPS deployment guide
- `DEPLOY_QUICK.md` - Quick deployment reference
- `DATABASE_SETUP.md` - Database configuration & maintenance

## 🛠️ Tech Stack

- **Backend**: Flask 3.0, SQLAlchemy, yt-dlp
- **Database**: SQLite (default), PostgreSQL/MySQL supported
- **Frontend**: Vanilla JavaScript, CSS
- **Libraries**: 
  - Video: yt-dlp, instaloader
  - PDF: PyPDF2, pdf2docx, pdf2image
  - Image: Pillow, OpenCV, rembg
  - Office: python-docx, openpyxl

## 📦 Requirements

- Python 3.10+
- FFmpeg (for video processing)
- Poppler (for PDF to image conversion)

## 🔒 Security Features

- Rate limiting (Flask-Limiter)
- File type validation
- Size restrictions
- CORS configuration
- Secret key management

## 🧹 Auto Cleanup

Automatic file cleanup runs every hour:
- Removes files older than retention period (default: 24h)
- Cleans expired database records
- Logs disk space freed

## 📄 License

MIT License

## 👤 Author

**donan2290**
- Email: donan2290@gmail.com
- GitHub: [@donan2290-lang](https://github.com/donan2290-lang)

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

## ⭐ Show Your Support

Give a ⭐️ if this project helped you!

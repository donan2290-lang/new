# Deploy ke Hostinger - Panduan Lengkap

## ⚠️ PENTING: Batasan Shared Hosting

**Shared Hosting Hostinger TIDAK mendukung:**
- ❌ Install Python packages custom (yt-dlp, ffmpeg)
- ❌ Background processes
- ❌ Long-running tasks
- ❌ Heavy video processing

**Solusi untuk Shared Hosting:**

### Opsi 1: Hybrid Setup (Recommended)
- **Backend API** → Deploy ke platform gratis yang support Python:
  - **Railway.app** (gratis, support Python)
  - **Render.com** (gratis 750 jam/bulan)
  - **PythonAnywhere** (gratis dengan batasan)
  - **Fly.io** (gratis tier)
- **Frontend Statis** → Hostinger (HTML/CSS/JS)
- Frontend Hostinger fetch data dari Backend API

### Opsi 2: Full Deploy ke Platform Python
Skip Hostinger, deploy full app ke:
- **Railway** / **Render** / **PythonAnywhere**

### Opsi 3: Upgrade ke VPS Hostinger
Harga mulai ~Rp 45.000/bulan

---

## 🚀 Panduan Deploy: Opsi 1 (Hybrid - RECOMMENDED)

### **Bagian A: Deploy Backend API ke Railway.app (GRATIS)**

#### 1. Persiapan File untuk Railway

Buat file `railway.json`:
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

Buat file `Procfile`:
```
web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

Buat file `runtime.txt`:
```
python-3.10.11
```

#### 2. Setup Railway Account

1. Buka https://railway.app/
2. Sign up dengan GitHub
3. Klik **New Project**
4. Pilih **Deploy from GitHub repo**
5. Connect repository VideoDownloaderApp
6. Railway akan auto-detect Python dan deploy

#### 3. Set Environment Variables di Railway

Di Railway dashboard → Variables:
```
FLASK_ENV=production
SECRET_KEY=your-secret-key-12345
FLASK_DEBUG=False
PORT=8080
MAX_FILE_SIZE_MB=50
MAX_DOWNLOAD_SIZE_MB=500
DATABASE_URL=sqlite:///snapload.db
DOWNLOAD_RETENTION_HOURS=24
RATE_LIMIT_ENABLED=True
AUTO_CLEANUP_ENABLED=True
```

#### 4. Deploy & Get API URL

Railway akan auto-deploy dan berikan URL seperti:
```
https://your-app.railway.app
```

**Catat URL ini!**

---

### **Bagian B: Deploy Frontend ke Hostinger Shared Hosting**

#### 1. Modifikasi Frontend untuk Fetch ke Railway API

Buat file `static/config.js`:
```javascript
// API Configuration
const API_BASE_URL = 'https://your-app.railway.app';  // Ganti dengan URL Railway

// Update semua fetch calls
async function getDownloadUrl(url, platform) {
    const response = await fetch(`${API_BASE_URL}/api/get-download-url`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, platform })
    });
    return response.json();
}
```

Update `static/script.js`, tambahkan di bagian atas:
```javascript
// Import API config
const API_BASE_URL = 'https://your-app.railway.app';  // URL Railway Anda

// Update semua endpoint
// Contoh: fetch('/api/download') → fetch(`${API_BASE_URL}/api/download`)
```

#### 2. Upload ke Hostinger via File Manager

1. Login hPanel Hostinger
2. Pilih **Website** → **File Manager**
3. Masuk folder `public_html`
4. Upload file:
   ```
   public_html/
   ├── index.html (dari templates/index.html)
   ├── image_converter.html (dari templates/)
   ├── pdf_converter.html (dari templates/)
   ├── static/
   │   ├── config.js (baru)
   │   ├── script.js (sudah dimodifikasi)
   │   ├── image-converter.js
   │   ├── pdf-converter.js
   │   └── style.css
   ```

#### 3. Update CORS di Backend (Railway)

Edit `app.py`, update CORS:
```python
CORS(app, resources={
    r"/*": {
        "origins": [
            "https://yourdomain.com",  # Domain Hostinger
            "http://yourdomain.com",
            "https://your-app.railway.app"
        ]
    }
})
```

Commit & push ke GitHub, Railway auto-redeploy.

---

## 🚀 Panduan Deploy: Opsi 2 (Full ke Railway)

Lebih simple, skip Hostinger:

### 1. Push Code ke GitHub
```bash
cd "C:\Users\User\Desktop\download idlix\VideoDownloaderApp"
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/username/VideoDownloaderApp.git
git push -u origin main
```

### 2. Deploy ke Railway
1. https://railway.app/ → New Project
2. Deploy from GitHub
3. Select repository
4. Set environment variables
5. Deploy!

### 3. Custom Domain (Opsional)
- Railway berikan domain: `your-app.railway.app`
- Bisa tambah custom domain dari Hostinger:
  - Di Railway → Settings → Domains → Add custom domain
  - Di Hostinger DNS → Add CNAME: `www` → `your-app.railway.app`

---

## 🚀 Panduan Deploy: Opsi 3 (VPS Hostinger)

Jika Anda upgrade ke VPS Hostinger:

### **Step 1: Setup VPS di Hostinger**

1. Login ke hPanel Hostinger
2. Upgrade ke **VPS Hosting**
3. Pilih paket (VPS 2 recommended: ~Rp 90.000/bulan)
4. Pilih OS: **Ubuntu 22.04**
5. Catat IP Address & root password

### **Step 2: Koneksi SSH ke VPS**

```bash
# Dari komputer lokal
ssh root@your-vps-ip
```

### **Step 3: Update System & Install Dependencies**

```bash
# Update system
apt update && apt upgrade -y

# Install Python & essential tools
apt install python3.10 python3.10-venv python3-pip git nginx supervisor -y

# Install ffmpeg untuk video processing
apt install ffmpeg -y

# Install build tools
apt install build-essential libssl-dev libffi-dev python3-dev -y
```

### **Step 4: Buat User Non-Root**

```bash
# Buat user untuk aplikasi
adduser appuser
usermod -aG sudo appuser

# Switch ke user baru
su - appuser
```

### **Step 5: Upload Aplikasi**

**Opsi A: Via Git (Recommended)**
```bash
cd /home/appuser
git clone https://your-repo-url.git VideoDownloaderApp
cd VideoDownloaderApp
```

**Opsi B: Via SFTP/SCP**
```bash
# Dari komputer lokal
scp -r "C:\Users\User\Desktop\download idlix\VideoDownloaderApp" appuser@your-vps-ip:/home/appuser/
```

### **Step 6: Setup Virtual Environment**

```bash
cd /home/appuser/VideoDownloaderApp

# Buat virtual environment
python3 -m venv venv

# Aktivasi
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### **Step 7: Konfigurasi Environment**

```bash
# Buat file .env
nano .env
```

Isi `.env`:
```bash
# Flask
FLASK_ENV=production
SECRET_KEY=your-super-secret-key-change-this-123456789
FLASK_DEBUG=False

# Server
HOST=0.0.0.0
PORT=5000

# File limits
MAX_FILE_SIZE_MB=50
MAX_DOWNLOAD_SIZE_MB=500

# Database
DATABASE_URL=sqlite:///snapload.db
DOWNLOAD_RETENTION_HOURS=24

# Rate Limiting
RATE_LIMIT_ENABLED=True
RATE_LIMIT_DEFAULT=100 per hour
RATE_LIMIT_DOWNLOAD=10 per hour

# Cleanup
AUTO_CLEANUP_ENABLED=True
CLEANUP_INTERVAL_HOURS=1
CLEANUP_MAX_AGE_HOURS=24

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

### **Step 8: Initialize Database**

```bash
source venv/bin/activate
python init_db.py
```

### **Step 9: Test Aplikasi**

```bash
# Test run
python app.py

# Jika berhasil, tekan Ctrl+C untuk stop
```

### **Step 10: Setup Gunicorn**

```bash
# Test gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 app:app

# Jika OK, Ctrl+C untuk stop
```

### **Step 11: Setup Supervisor (Auto-restart)**

```bash
sudo nano /etc/supervisor/conf.d/videodownloader.conf
```

Isi file:
```ini
[program:videodownloader]
directory=/home/appuser/VideoDownloaderApp
command=/home/appuser/VideoDownloaderApp/venv/bin/gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 --access-logfile logs/access.log --error-logfile logs/error.log app:app
user=appuser
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
stderr_logfile=/var/log/videodownloader.err.log
stdout_logfile=/var/log/videodownloader.out.log
environment=PATH="/home/appuser/VideoDownloaderApp/venv/bin"
```

Aktifkan:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start videodownloader
sudo supervisorctl status
```

### **Step 12: Setup Nginx (Reverse Proxy)**

```bash
sudo nano /etc/nginx/sites-available/videodownloader
```

Isi:
```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    
    client_max_body_size 500M;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeout untuk download besar
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
        send_timeout 300;
    }
    
    location /static {
        alias /home/appuser/VideoDownloaderApp/static;
        expires 30d;
    }
}
```

Aktifkan:
```bash
sudo ln -s /etc/nginx/sites-available/videodownloader /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### **Step 13: Setup Domain di Hostinger**

1. Di hPanel → Domain → Manage
2. Tambah A Record:
   - Name: `@` (atau subdomain)
   - Points to: `IP VPS Anda`
   - TTL: 3600

3. Tunggu propagasi DNS (5-30 menit)

### **Step 14: Setup SSL (HTTPS)**

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Generate SSL certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Auto-renewal test
sudo certbot renew --dry-run
```

### **Step 15: Setup Firewall**

```bash
# Setup UFW
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

---

## 🔧 Maintenance Commands

### Check Status
```bash
# Supervisor
sudo supervisorctl status videodownloader

# Nginx
sudo systemctl status nginx

# Logs
tail -f /var/log/videodownloader.out.log
tail -f logs/app.log
```

### Restart Aplikasi
```bash
sudo supervisorctl restart videodownloader
```

### Update Aplikasi
```bash
cd /home/appuser/VideoDownloaderApp
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo supervisorctl restart videodownloader
```

### Clean Old Files
```bash
# Manual cleanup
cd /home/appuser/VideoDownloaderApp
rm -rf uploads/* outputs/* logs/*.log.*
```

---

## 📊 Monitoring

### Setup Log Rotation
```bash
sudo nano /etc/logrotate.d/videodownloader
```

```
/home/appuser/VideoDownloaderApp/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 appuser appuser
    sharedscripts
    postrotate
        supervisorctl restart videodownloader > /dev/null
    endscript
}
```

### Setup Disk Space Alert
```bash
# Add to crontab
crontab -e
```

```bash
# Check disk every hour
0 * * * * df -h /home | awk '$5 > 80 {print "Disk usage > 80%: " $5}' | mail -s "Disk Alert" your@email.com
```

---

## 🛡️ Security Best Practices

1. **Ganti Secret Key** di `.env`
2. **Disable root SSH**:
   ```bash
   sudo nano /etc/ssh/sshd_config
   # Set: PermitRootLogin no
   sudo systemctl restart sshd
   ```

3. **Rate Limiting** sudah aktif via Flask-Limiter

4. **Backup Regular**:
   ```bash
   # Backup database
   crontab -e
   # Daily backup at 2 AM
   0 2 * * * cp /home/appuser/VideoDownloaderApp/instance/snapload.db /home/appuser/backups/snapload-$(date +\%Y\%m\%d).db
   ```

---

## 💰 Estimasi Biaya

### Opsi 1: Hybrid (Shared Hosting + Railway)
- **Hostinger Shared**: Rp 20.000 - 50.000/bulan
- **Railway Backend**: GRATIS (500 jam/bulan) atau $5/bulan unlimited
- **Total**: ~Rp 20.000 - 50.000/bulan

### Opsi 2: Full Railway
- **Railway**: GRATIS (hobby tier) atau $5/bulan
- **Domain dari Hostinger**: Rp 30.000/tahun (opsional)
- **Total**: GRATIS atau ~$5/bulan

### Opsi 3: VPS Hostinger
- **VPS 1**: ~Rp 45.000/bulan (testing)
- **VPS 2**: ~Rp 90.000/bulan (production - recommended)
- **VPS 4**: ~Rp 180.000/bulan (high traffic)

**Rekomendasi: Opsi 2 (Full Railway) - paling mudah & murah!**

---

## 🆘 Troubleshooting

### Error: Permission Denied
```bash
sudo chown -R appuser:appuser /home/appuser/VideoDownloaderApp
sudo chmod -R 755 /home/appuser/VideoDownloaderApp
```

### Error: Port Already in Use
```bash
sudo netstat -tlnp | grep :5000
sudo kill -9 <PID>
```

### Error: Database Locked
```bash
# Restart app
sudo supervisorctl restart videodownloader
```

### Error: Out of Disk Space
```bash
# Clean old files
cd /home/appuser/VideoDownloaderApp
python3 -c "from services import task_service; from flask import Flask; from config import config; app = Flask(__name__); app.config.from_object(config['production']); from extensions import db; db.init_app(app); with app.app_context(): task_service.cleanup_expired_tasks()"
```

---

## ✅ Checklist Deploy

- [ ] VPS dibeli & setup
- [ ] SSH access configured
- [ ] Dependencies installed
- [ ] Aplikasi uploaded
- [ ] Virtual environment created
- [ ] .env configured
- [ ] Database initialized
- [ ] Supervisor configured
- [ ] Nginx configured
- [ ] Domain pointed
- [ ] SSL installed
- [ ] Firewall enabled
- [ ] Monitoring setup
- [ ] Backup configured

---

## 🎯 URL Akhir

Setelah semua selesai, aplikasi bisa diakses di:
- **HTTP**: http://your-domain.com
- **HTTPS**: https://your-domain.com (Recommended)

---

**Support:**
- Hostinger Support: https://www.hostinger.co.id/tutorial
- Dokumentasi: DATABASE_SETUP.md

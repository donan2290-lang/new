# Deploy VideoDownloaderApp - Quick Start

## ✅ Untuk Shared Hosting Hostinger

Shared hosting **TIDAK bisa** menjalankan Python app secara langsung.

### Solusi Terbaik: Deploy ke Railway (GRATIS!)

Railway adalah platform cloud yang support Python, gratis 500 jam/bulan.

---

## 🚀 Langkah Deploy (15 Menit)

### 1. Push ke GitHub

```bash
# Di folder project
git init
git add .
git commit -m "Initial commit"

# Buat repo di GitHub, lalu:
git remote add origin https://github.com/username/VideoDownloaderApp.git
git push -u origin main
```

### 2. Deploy ke Railway

1. Buka https://railway.app/
2. **Sign Up** dengan GitHub
3. Klik **New Project**
4. Pilih **Deploy from GitHub repo**
5. Pilih repository **VideoDownloaderApp**
6. Railway akan auto-deploy!

### 3. Set Environment Variables

Di Railway dashboard → **Variables**:

```
FLASK_ENV=production
SECRET_KEY=ganti-dengan-random-string-panjang
FLASK_DEBUG=False
PORT=8080
MAX_FILE_SIZE_MB=50
MAX_DOWNLOAD_SIZE_MB=500
DATABASE_URL=sqlite:///snapload.db
DOWNLOAD_RETENTION_HOURS=24
RATE_LIMIT_ENABLED=True
AUTO_CLEANUP_ENABLED=True
```

### 4. Selesai! ✅

Railway berikan URL:
```
https://videodownloaderapp-production.up.railway.app
```

Buka URL tersebut, app sudah live!

---

## 🌐 Custom Domain (Opsional)

### Gunakan Domain dari Hostinger

1. **Di Railway**:
   - Settings → Domains → Custom Domain
   - Masukkan: `download.yourdomain.com`
   - Catat CNAME value

2. **Di Hostinger hPanel**:
   - Domain → DNS/Name Servers → Manage
   - Add CNAME Record:
     - Name: `download`
     - Points to: (CNAME dari Railway)
   - Save

3. Tunggu 5-30 menit untuk propagasi DNS

---

## 💡 Tips

### Gratis selamanya?
- Railway: 500 jam/bulan gratis
- Cukup untuk ~20 hari uptime
- Upgrade $5/bulan untuk unlimited

### Performa
- Railway lebih cepat dari VPS murah
- Auto-scale sesuai traffic
- SSL/HTTPS otomatis

### Monitoring
- Railway dashboard: Logs, Metrics, Deployments
- Auto-restart jika crash

---

## 🆘 Troubleshooting

### Error: Build Failed
```bash
# Pastikan file ada:
- requirements.txt
- Procfile
- railway.json
- runtime.txt
```

### Error: App Crashed
Check logs di Railway dashboard, biasanya:
- Environment variables kurang
- Port tidak match (harus $PORT)

### Error: CORS
Update CORS di `app.py`:
```python
CORS(app, resources={r"/*": {"origins": "*"}})  # Allow all
```

---

## 📚 Resources

- Railway Docs: https://docs.railway.app/
- Railway Templates: https://railway.app/templates
- GitHub: Upload code dulu sebelum deploy

---

**Selamat mencoba! 🎉**

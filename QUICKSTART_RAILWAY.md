# 🚂 Quick Start - Deploy ke Railway

## Setup Cepat (5 Menit)

### 1. Push ke GitHub (Jika Belum)
```bash
git add .
git commit -m "Prepare for Railway deployment"
git push origin main
```

### 2. Deploy di Railway

**Option A: Via Browser (Termudah)**
1. Buka https://railway.app/
2. Login dengan GitHub Student account
3. Klik "New Project" → "Deploy from GitHub repo"
4. Pilih: `donan2290-lang/VideoDownloaderApp`
5. Railway auto-detect & deploy! ✅

**Option B: Via CLI**
```bash
# Install Railway CLI
npm i -g @railway/cli

# Login & deploy
railway login
railway init
railway up
```

### 3. Set Environment Variables (PENTING!)

**Generate SECRET_KEY dulu:**
```bash
# PowerShell
python -c "import secrets; print(secrets.token_hex(32))"
```

**Set di Railway Dashboard:**
```
Settings → Variables → Add Variable
```

**Minimum Variables:**
```
SECRET_KEY=<hasil-generate-tadi>
FLASK_ENV=production
```

**Recommended Variables:**
```
MAX_FILE_SIZE_MB=50
MAX_DOWNLOAD_SIZE_MB=500
RATE_LIMIT_ENABLED=True
AUTO_CLEANUP_ENABLED=True
```

### 4. Done! 🎉

URL: `https://your-app.up.railway.app`

---

## 📋 Checklist

- [ ] Repo di GitHub
- [ ] Deploy ke Railway
- [ ] Set SECRET_KEY
- [ ] Test URL works
- [ ] (Optional) Custom domain

## 🔧 Files Yang Railway Pakai

- ✅ `railway.json` - Config deploy
- ✅ `requirements.txt` - Dependencies
- ✅ `runtime.txt` - Python version (3.10.11)
- ✅ `Procfile` - Backup start command

## 💰 Biaya

**GitHub Student Pack:**
- $5/month kredit gratis
- ~500 jam execution/bulan
- Cukup untuk traffic menengah

## 📚 Dokumentasi Lengkap

Lihat `RAILWAY_DEPLOY.md` untuk panduan detail.

## 🆘 Troubleshooting Cepat

**Build Failed?**
```bash
railway logs
```

**App Crash?**
- Cek environment variables sudah diset
- Cek logs untuk error message

**Port Error?**
- Railway auto-set PORT, app sudah handle ini ✅

---

**Need Help?** Baca: `RAILWAY_DEPLOY.md`

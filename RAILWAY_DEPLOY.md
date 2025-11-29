# Deploy ke Railway - Panduan Lengkap

## 🚀 Langkah-langkah Deploy

### 1. Persiapan Akun
1. Daftar di [Railway](https://railway.app/) menggunakan GitHub Student account
2. Dapatkan $5/bulan kredit gratis
3. Connect GitHub account

### 2. Deploy Aplikasi

#### Opsi A: Deploy via Dashboard (Termudah)
1. Login ke Railway Dashboard
2. Klik **"New Project"**
3. Pilih **"Deploy from GitHub repo"**
4. Pilih repository: `donan2290-lang/VideoDownloaderApp`
5. Railway akan otomatis detect Python app dan deploy

#### Opsi B: Deploy via Railway CLI
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link project (di folder project)
railway link

# Deploy
railway up
```

### 3. Environment Variables (WAJIB)

Setelah deploy, tambahkan environment variables di Railway Dashboard:

**Settings > Variables** atau via CLI:
```bash
railway variables set SECRET_KEY=<generate-random-string-panjang>
railway variables set FLASK_ENV=production
railway variables set MAX_FILE_SIZE_MB=50
railway variables set MAX_DOWNLOAD_SIZE_MB=500
railway variables set RATE_LIMIT_ENABLED=True
railway variables set AUTO_CLEANUP_ENABLED=True
```

**Environment Variables yang Direkomendasikan:**
```env
# Security (WAJIB)
SECRET_KEY=your-super-secret-random-key-min-32-chars

# Environment
FLASK_ENV=production
FLASK_DEBUG=False

# File Limits
MAX_FILE_SIZE_MB=50
MAX_DOWNLOAD_SIZE_MB=500
DOWNLOAD_RETENTION_HOURS=24

# Rate Limiting
RATE_LIMIT_ENABLED=True
RATE_LIMIT_DEFAULT=100 per hour
RATE_LIMIT_DOWNLOAD=10 per hour
RATE_LIMIT_CONVERT=20 per hour

# Auto Cleanup
AUTO_CLEANUP_ENABLED=True
CLEANUP_INTERVAL_HOURS=1
CLEANUP_MAX_AGE_HOURS=24

# Language
DEFAULT_LANGUAGE=id
SUPPORTED_LANGUAGES=id,en
```

### 4. Generate SECRET_KEY

**Cara 1 - Python:**
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**Cara 2 - PowerShell:**
```powershell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | % {[char]$_})
```

### 5. Database (Opsional)

Jika butuh database persistent:
1. Di Railway Dashboard, klik **"New"** > **"Database"** > **"PostgreSQL"**
2. Railway akan auto-generate `DATABASE_URL`
3. Update `config.py` untuk gunakan PostgreSQL

### 6. Custom Domain (Opsional)

**Gunakan Domain Gratis dari GitHub Student Pack:**
- Namecheap: .me domain (1 tahun)
- Name.com: .tech domain (1 tahun)

**Setup di Railway:**
1. Settings > Domains
2. Add Custom Domain
3. Update DNS records sesuai petunjuk Railway

### 7. Monitoring

**Railway menyediakan:**
- Logs real-time: Dashboard > Logs
- Metrics: CPU, Memory, Network usage
- Build history
- Deployment status

**CLI Monitoring:**
```bash
# View logs
railway logs

# Check status
railway status

# View variables
railway variables
```

## 📊 Resource Limits Railway

**Free Tier ($5/month kredit):**
- 500 hours execution time/month
- 512MB RAM (shared)
- 1GB disk space
- Sleeping setelah 30 min tidak aktif

**Starter Tier ($5/month):**
- $5 kredit
- 8GB RAM
- 100GB disk space
- No sleeping

## 🔧 Troubleshooting

### Build Failed
```bash
# Cek logs
railway logs --deployment <deployment-id>

# Rebuild
railway up --force
```

### App Crash
- Cek logs untuk error message
- Pastikan semua dependencies di `requirements.txt`
- Cek environment variables

### Port Error
Railway otomatis set `$PORT`, pastikan app bind ke:
```python
PORT = int(os.getenv('PORT', 5000))
```

### Memory Issues
Kurangi workers di `railway.json`:
```json
"startCommand": "gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120"
```

## 🔗 URL Aplikasi

Setelah deploy berhasil:
- URL akan berbentuk: `https://your-app.up.railway.app`
- Atau custom domain jika sudah setup

## 📝 Update Aplikasi

### Auto Deploy (Recommended)
Railway otomatis deploy saat push ke GitHub:
```bash
git add .
git commit -m "Update aplikasi"
git push origin main
```

### Manual Deploy
```bash
railway up
```

## ✅ Checklist Deploy

- [ ] Repository sudah di GitHub
- [ ] File `railway.json` ada
- [ ] File `requirements.txt` lengkap
- [ ] File `Procfile` atau `railway.json` ada start command
- [ ] Environment variables sudah diset
- [ ] SECRET_KEY sudah diganti (bukan default)
- [ ] Test lokal berhasil
- [ ] Push ke GitHub
- [ ] Deploy di Railway
- [ ] Test URL production

## 🎯 Fitur Railway yang Berguna

1. **Preview Deployments** - Test changes sebelum merge
2. **Rollback** - Kembali ke deployment sebelumnya
3. **Cron Jobs** - Schedule tasks (upgrade plan)
4. **Environment Groups** - Kelola multiple environments
5. **GitHub Integration** - Auto deploy on push

## 💡 Tips

1. **Gunakan Railway Postgres** untuk database persistent
2. **Enable Cloudflare** untuk CDN gratis
3. **Monitor usage** untuk tidak over budget
4. **Setup health check endpoint** untuk monitoring
5. **Gunakan Redis** untuk rate limiting (lebih baik dari memory)

## 🆘 Support

- Railway Docs: https://docs.railway.app/
- Discord Community: https://discord.gg/railway
- GitHub Issues: https://github.com/railwayapp/railway

---

**Happy Deploying! 🚀**

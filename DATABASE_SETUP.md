# Setup Database untuk VideoDownloaderApp

## ✅ Database Sudah Terinstall!

Database SQLite sudah berhasil dikonfigurasi dan berjalan.

### 📁 Lokasi Database
- **File**: `instance/snapload.db`
- **Path**: `c:\Users\User\Desktop\download idlix\VideoDownloaderApp\instance\snapload.db`

### 🗄️ Tabel Database

**download_tasks** - Menyimpan tracking download/conversion:
- `id` - Primary key (UUID)
- `session_id` - Session identifier (unique)
- `platform` - Platform sumber (youtube, instagram, dll)
- `source_url` - URL sumber video
- `direct_url` - URL download langsung
- `requested_filename` - Nama file yang diminta
- `storage_path` - Lokasi file sementara
- `storage_type` - Tipe storage (temp, output, upload)
- `file_size` - Ukuran file (bytes)
- `status` - Status task (pending, processing, completed, error)
- `message` - Pesan status
- `last_progress` - Data progress (JSON)
- `last_accessed_at` - Terakhir diakses
- `created_at` - Waktu dibuat
- `updated_at` - Terakhir diupdate
- `expires_at` - Waktu kadaluarsa

### 🔧 Cara Menggunakan

#### 1. Inisialisasi Database (sudah dilakukan)
```bash
python init_db.py
```

#### 2. Test Database
```bash
python test_db.py
```

#### 3. Gunakan di Aplikasi
```python
from services import task_service

# Buat/update task
task = task_service.upsert_task('session-123', {
    'platform': 'youtube',
    'source_url': 'https://youtube.com/watch?v=xxx'
})

# Update status
task_service.mark_status('session-123', 'processing', 'Downloading...')

# Register file storage
task_service.register_storage('session-123', '/path/to/file.mp4', 
                              storage_type='temp', file_size=1024000)

# Cleanup expired tasks
removed, size = task_service.cleanup_expired_tasks()
```

### 🔄 Migrasi ke Database Lain

Jika ingin pindah dari SQLite ke PostgreSQL/MySQL:

#### PostgreSQL:
```bash
# Install driver
pip install psycopg2-binary

# Set environment variable
$env:DATABASE_URL="postgresql://user:password@localhost/dbname"
```

#### MySQL:
```bash
# Install driver
pip install pymysql

# Set environment variable
$env:DATABASE_URL="mysql+pymysql://user:password@localhost/dbname"
```

### 📊 Retention Settings

Default: File dihapus otomatis setelah **24 jam**

Ubah di `.env`:
```
DOWNLOAD_RETENTION_HOURS=48  # 2 hari
CLEANUP_INTERVAL_HOURS=1     # Cek setiap 1 jam
```

### 🧹 Auto Cleanup

Cleanup scheduler otomatis berjalan setiap jam untuk:
- Menghapus file kadaluarsa dari disk
- Menghapus record database yang expired
- Logging size disk yang dibebaskan

### 🛠️ Maintenance

#### Lihat semua tasks:
```python
from models import DownloadTask
from extensions import db

with app.app_context():
    tasks = DownloadTask.query.all()
    for task in tasks:
        print(f"{task.session_id}: {task.status}")
```

#### Manual cleanup:
```python
from services import task_service

removed, size_freed = task_service.cleanup_expired_tasks()
print(f"Removed {removed} tasks, freed {size_freed} bytes")
```

### ✅ Status

- [x] Database configured
- [x] Tables created
- [x] Models tested
- [x] Task service ready
- [x] Auto cleanup enabled
- [x] Integration with app.py

### 🚀 Next Steps

Database siap digunakan! Aplikasi akan otomatis:
1. Track semua download/conversion
2. Simpan metadata file
3. Hapus file expired otomatis
4. Cegah folder penuh

Jalankan aplikasi: `python app.py`

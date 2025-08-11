import os
import shutil
import json
import zipfile
from pathlib import Path
from datetime import datetime
from config import DATA_DIR, CHROMA_PERSIST_DIR, UPLOAD_DIR, IS_RAILWAY

class BackupManager:
    def __init__(self):
        self.backup_dir = Path(DATA_DIR) / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
    def create_backup(self) -> str:
        """Create a complete backup of all data"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"mcpress_backup_{timestamp}.zip"
        backup_path = self.backup_dir / backup_name
        
        print(f"🔄 Creating backup: {backup_name}")
        
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Backup ChromaDB
            chroma_path = Path(CHROMA_PERSIST_DIR)
            if chroma_path.exists():
                for file in chroma_path.rglob('*'):
                    if file.is_file():
                        arcname = f"chroma_db/{file.relative_to(chroma_path)}"
                        zipf.write(file, arcname)
                        
            # Backup uploaded PDFs
            upload_path = Path(UPLOAD_DIR)
            if upload_path.exists():
                for file in upload_path.rglob('*.pdf'):
                    if file.is_file():
                        arcname = f"uploads/{file.relative_to(upload_path)}"
                        zipf.write(file, arcname)
                        
            # Create metadata
            metadata = {
                "timestamp": timestamp,
                "railway_environment": IS_RAILWAY,
                "data_dir": str(DATA_DIR),
                "chroma_dir": CHROMA_PERSIST_DIR,
                "upload_dir": UPLOAD_DIR,
                "file_count": len(list(upload_path.rglob('*.pdf'))) if upload_path.exists() else 0
            }
            zipf.writestr("backup_metadata.json", json.dumps(metadata, indent=2))
            
        print(f"✅ Backup created: {backup_path} ({backup_path.stat().st_size // (1024*1024)} MB)")
        
        # Keep only last 5 backups
        self._cleanup_old_backups()
        
        return str(backup_path)
        
    def restore_backup(self, backup_path: str) -> bool:
        """Restore from backup"""
        backup_file = Path(backup_path)
        if not backup_file.exists():
            print(f"❌ Backup file not found: {backup_path}")
            return False
            
        print(f"🔄 Restoring from backup: {backup_file.name}")
        
        try:
            with zipfile.ZipFile(backup_file, 'r') as zipf:
                # Extract ChromaDB
                chroma_files = [f for f in zipf.namelist() if f.startswith('chroma_db/')]
                for file in chroma_files:
                    target = Path(CHROMA_PERSIST_DIR) / file[10:]  # Remove 'chroma_db/' prefix
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zipf.open(file) as src, open(target, 'wb') as dst:
                        shutil.copyfileobj(src, dst)
                        
                # Extract uploads
                upload_files = [f for f in zipf.namelist() if f.startswith('uploads/')]
                for file in upload_files:
                    target = Path(UPLOAD_DIR) / file[8:]  # Remove 'uploads/' prefix
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zipf.open(file) as src, open(target, 'wb') as dst:
                        shutil.copyfileobj(src, dst)
                        
            print("✅ Backup restored successfully")
            return True
            
        except Exception as e:
            print(f"❌ Restore failed: {e}")
            return False
            
    def _cleanup_old_backups(self):
        """Keep only the 5 most recent backups"""
        backups = sorted(self.backup_dir.glob("mcpress_backup_*.zip"), 
                        key=lambda x: x.stat().st_mtime, reverse=True)
        
        for old_backup in backups[5:]:  # Keep only first 5
            old_backup.unlink()
            print(f"🗑️  Removed old backup: {old_backup.name}")
            
    def list_backups(self) -> list:
        """List available backups"""
        backups = sorted(self.backup_dir.glob("mcpress_backup_*.zip"), 
                        key=lambda x: x.stat().st_mtime, reverse=True)
        return [str(b) for b in backups]
        
    def auto_backup_on_startup(self):
        """Create automatic backup if data exists"""
        chroma_exists = Path(CHROMA_PERSIST_DIR).exists()
        uploads_exist = Path(UPLOAD_DIR).exists() and any(Path(UPLOAD_DIR).glob('*.pdf'))
        
        if chroma_exists or uploads_exist:
            print("📦 Data detected on startup - creating automatic backup...")
            backup_path = self.create_backup()
            print(f"📦 Startup backup completed: {Path(backup_path).name}")
        else:
            print("📦 No existing data found - skipping startup backup")

# Global backup manager instance
backup_manager = BackupManager()
#!/usr/bin/env python3
"""
Web endpoint to trigger batch uploads - accessible via Railway URL
"""
import asyncio
import subprocess
import sys
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse
import os

app = FastAPI()

# Global status tracking
upload_status = {
    "running": False,
    "last_run": None,
    "result": None,
    "logs": []
}

def run_upload_batch(batch_size: int = 15):
    """Run upload in background"""
    global upload_status
    
    upload_status["running"] = True
    upload_status["last_run"] = datetime.now().isoformat()
    upload_status["logs"] = [f"Starting batch upload with {batch_size} PDFs..."]
    
    try:
        # Run the upload script
        result = subprocess.run([
            sys.executable,
            "/app/backend/railway_batch_upload.py",
            "--batch-size", str(batch_size)
        ], 
        capture_output=True, 
        text=True, 
        timeout=1800  # 30 minutes
        )
        
        upload_status["result"] = {
            "returncode": result.returncode,
            "stdout": result.stdout[-2000:],  # Last 2000 chars
            "stderr": result.stderr[-1000:] if result.stderr else None
        }
        upload_status["logs"].append(f"Upload completed with code {result.returncode}")
        
    except subprocess.TimeoutExpired:
        upload_status["result"] = {"error": "Upload timed out after 30 minutes"}
        upload_status["logs"].append("Upload timed out")
    except Exception as e:
        upload_status["result"] = {"error": str(e)}
        upload_status["logs"].append(f"Upload error: {e}")
    finally:
        upload_status["running"] = False

@app.get("/upload/trigger/{batch_size}")
async def trigger_upload(batch_size: int, background_tasks: BackgroundTasks):
    """Trigger batch upload"""
    if upload_status["running"]:
        return {"error": "Upload already running", "status": upload_status}
    
    background_tasks.add_task(run_upload_batch, batch_size)
    return {"message": f"Upload started for {batch_size} PDFs", "status": "started"}

@app.get("/upload/status")
async def get_upload_status():
    """Get upload status"""
    return upload_status

@app.get("/upload/dashboard")
async def upload_dashboard():
    """Simple HTML dashboard for triggering uploads"""
    html = f"""
    <html>
    <head><title>Railway PDF Upload Dashboard</title></head>
    <body style="font-family: Arial; padding: 20px;">
        <h1>🚂 Railway PDF Upload Dashboard</h1>
        
        <div style="background: #f0f0f0; padding: 15px; margin: 10px 0; border-radius: 5px;">
            <h3>Current Status</h3>
            <p><strong>Running:</strong> {upload_status['running']}</p>
            <p><strong>Last Run:</strong> {upload_status['last_run'] or 'Never'}</p>
        </div>
        
        <div style="margin: 20px 0;">
            <h3>Quick Actions</h3>
            <a href="/upload/trigger/15" style="background: #007cba; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 5px;">
                📤 Upload 15 PDFs
            </a>
            <a href="/upload/trigger/10" style="background: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 5px;">
                📤 Upload 10 PDFs
            </a>
            <a href="/upload/status" style="background: #6c757d; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin: 5px;">
                📊 Check Status
            </a>
        </div>
        
        <div style="background: #e9ecef; padding: 15px; margin: 10px 0; border-radius: 5px;">
            <h3>Recent Logs</h3>
            <pre>{chr(10).join(upload_status['logs'][-10:])}</pre>
        </div>
        
        <script>
            // Auto-refresh every 30 seconds
            setTimeout(() => location.reload(), 30000);
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
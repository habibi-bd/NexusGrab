import asyncio
import os
from fastapi import FastAPI, Depends, WebSocket, WebSocketDisconnect, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database import engine, Base, get_db
from app.models import DownloadAnalytics
from app.services.downloader import run_yt_dlp_download, ProgressHookWrapper

Base.metadata.create_all(bind=engine)
app = FastAPI(title="NexusGrab Premium Engine")
templates = Jinja2Templates(directory="app/templates")


@app.get("/download-file")
async def download_file_to_pc(path: str, name: str):
    if os.path.exists(path):
        return FileResponse(path, media_type="application/octet-stream", filename=name)
    return {"error": "Target download asset cache expired."}


@app.get("/")
async def read_root(request: Request, db: Session = Depends(get_db)):
    history = (
        db.query(DownloadAnalytics)
        .order_by(DownloadAnalytics.downloaded_at.desc())
        .limit(10)
        .all()
    )
    stats = db.query(DownloadAnalytics.domain).all()
    domain_counts = {}
    for entry in stats:
        domain_counts[entry.domain] = domain_counts.get(entry.domain, 0) + 1
    return templates.TemplateResponse(
        request, "index.html", {"history": history, "chart_data": domain_counts}
    )


@app.websocket("/ws/download")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()
    loop = asyncio.get_event_loop()

    try:
        data = await websocket.receive_json()
        video_url = data.get("url")

        hook = ProgressHookWrapper(websocket, loop)
        result = await asyncio.to_thread(run_yt_dlp_download, video_url, db, hook)

        # Pass asset descriptors down to frontend to construct custom video/audio elements
        await websocket.send_json(
            {
                "status": "completed",
                "file_url": f"/download-file?path={result['full_path']}&name={result['filename']}",
                "title": result["title"],
                "thumbnail": result["thumbnail"],
                "is_audio": result["is_audio"],
                "stream_route": f"/download-file?path={result['full_path']}&name={result['filename']}",
            }
        )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"status": "error", "message": str(e)})
    finally:
        await websocket.close()


import os
import shutil
import subprocess
import asyncio
import json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from typing import Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve Frontend Static Files
if os.path.exists("static"):
    app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")

@app.get("/")
async def read_root():
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return {"message": "Frontend not found. Please build the React app."}

UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    mtu: int = Form(...),
    delay: int = Form(...),
    ack: int = Form(...)
):
    try:
        # Save the file
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Prepare C command
        # Expected: ./upload_image <filename> <mtu> <delay> <ack>
        
        file_name = file.filename
        
        # Linux / WSL native execution
        # Ensure executable permission
        if os.path.exists("./upload_image") and not os.access("./upload_image", os.X_OK):
            subprocess.run(["chmod", "+x", "./upload_image"])

        # Setup environment variable for the library
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = os.path.abspath("./lib") + ":" + env.get("LD_LIBRARY_PATH", "")

        full_cmd = [
            "./upload_image",
            f"{UPLOAD_DIR}/{file_name}",
            str(mtu),
            str(delay),
            str(ack)
        ]

        print(f"Running command: {full_cmd}")
        
        result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            env=env if env else os.environ,
            cwd=os.getcwd() 
        )

        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }

    except Exception as e:
        return HTTPException(status_code=500, detail=str(e))

@app.post("/upload-stream")
async def upload_file_stream(
    file: UploadFile = File(...),
    mtu: int = Form(...),
    delay: int = Form(...),
    ack: int = Form(...)
):
    """
    Stream file upload logs in real-time using Server-Sent Events (SSE)
    """
    try:
        # Save the file
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_name = file.filename

        # Ensure executable permission
        if os.path.exists("./upload_image") and not os.access("./upload_image", os.X_OK):
            subprocess.run(["chmod", "+x", "./upload_image"])

        # Setup environment variable for the library
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = os.path.abspath("./lib") + ":" + env.get("LD_LIBRARY_PATH", "")

        full_cmd = [
            "./upload_image",
            f"{UPLOAD_DIR}/{file_name}",
            str(mtu),
            str(delay),
            str(ack)
        ]

        async def event_generator():
            """Generate SSE events from subprocess output"""
            try:
                # Send initial status
                yield f"data: {json.dumps({'type': 'status', 'message': 'Starting file upload...'})}\n\n"
                
                # Start the process
                process = subprocess.Popen(
                    full_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,  # Line buffered
                    env=env,
                    cwd=os.getcwd()
                )

                # Stream output line by line
                while True:
                    line = process.stdout.readline()
                    if not line:
                        break
                    
                    # Send each line as an SSE event
                    yield f"data: {json.dumps({'type': 'log', 'message': line.rstrip()})}\n\n"
                    await asyncio.sleep(0.01)  # Small delay to prevent overwhelming the client

                # Wait for process to complete
                process.wait()

                # Send completion status
                if process.returncode == 0:
                    yield f"data: {json.dumps({'type': 'complete', 'message': 'Upload completed successfully', 'returncode': process.returncode})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'error', 'message': f'Upload failed with code {process.returncode}', 'returncode': process.returncode})}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': f'Error: {str(e)}'})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

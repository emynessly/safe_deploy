from fastapi import FastAPI, Request, Form, Header, UploadFile, File, HTTPException, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, JSONResponse
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from .schemas import UserCreate
import bleach, uuid, os, filetype, traceback
from .logger_config import logger

app = FastAPI()
templates = Jinja2Templates(directory="templates")

load_dotenv()
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    raise ValueError("ENCRYPTION_KEY not set in .env")
cipher = Fernet(ENCRYPTION_KEY.encode())

comments_db = []

users_db = [
    {"id": 1, "username": "alice", "role": "user"},
    {"id": 2, "username": "bob", "role": "user"},
    {"id": 3, "username": "admin", "role": "admin"},
]

files_db = [
    {"id": 1, "name": "alice_report.txt", "owner": "alice", "size": 1024, "is_encrypted": False},
    {"id": 2, "name": "bob_report.txt", "owner": "bob", "size": 2048, "is_encrypted": False},
    {"id": 3, "name": "admin_report.txt", "owner": "admin", "size": 512, "is_encrypted": False},
]

MAX_FILE_SIZE = 2 * 1024 * 1024

def get_current_user(username: str = Header(default="alice", alias="username")):
    return next((u for u in users_db if u["username"] == username), None)

def check_file_permissions(file_id: int, current_user: dict = Depends(get_current_user)):
    file = next((f for f in files_db if f["id"] == file_id), None)
    if not file:
        raise HTTPException(status_code=404, detail="Not found")
    if current_user["role"] == "admin":
        return file
    if file["owner"] == current_user["username"]:
        return file
    raise HTTPException(status_code=404, detail="Not found")

ALLOWED_TAGS = ['b', 'i', 'u', 'em', 'strong']

def clean_text(text: str) -> str:
    cleaned = bleach.clean(text, tags=ALLOWED_TAGS, strip=True)
    return cleaned

@app.get("/files/my")
def get_my_files(current_user: dict = Depends(get_current_user)):
    logger.info(f"User {current_user['username']} requested their files")
    my_files = [f for f in files_db if f["owner"] == current_user["username"]]
    return {"files": my_files}

@app.get("/files/all")
def get_all_files(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        logger.warning(f"User {current_user['username']} attempted to access /files/all (non-admin)")
        raise HTTPException(status_code=403, detail="Forbidden")
    logger.info(f"Admin {current_user['username']} requested all files")
    return {"files": files_db}

@app.get("/files/{file_id}")
def get_file(file: dict = Depends(check_file_permissions)):
    logger.info(f"File metadata requested: id={file['id']}, owner={file['owner']}")
    return {"id": file["id"], "name": file["name"], "owner": file["owner"], "size": file["size"]}

@app.delete("/files/{file_id}")
def delete_file(file_id: int, current_user: dict = Depends(get_current_user)):
    file = next((f for f in files_db if f["id"] == file_id), None)
    if not file:
        raise HTTPException(status_code=404, detail="Not found")
    if current_user["role"] != "admin" and file["owner"] != current_user["username"]:
        logger.warning(f"IDOR attempt: {current_user['username']} tried to delete file {file_id} owned by {file['owner']}")
        raise HTTPException(status_code=404, detail="Not found")
    files_db.remove(file)
    logger.info(f"File deleted: id={file_id} by {current_user['username']}")
    return {"msg": "File deleted"}

@app.post("/registration")
async def registration(user: UserCreate):
    logger.info(f"User registered: {user.username}")
    return {"msg": "User created", "user": user.username}

@app.get("/comments")
def get_comments(request: Request):
    return templates.TemplateResponse("comments.html", {"request": request, "comments": comments_db})

@app.post("/comments")
def post_comments(request: Request, text: str = Form(...)):
    cleaned = clean_text(text)
    comments_db.append(cleaned)
    return templates.TemplateResponse("comments.html", {"request": request, "comments": comments_db})

@app.get("/clear")
def clear():
    comments_db.clear()
    return {"msg": "Comments cleared"}

@app.post("/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    encrypt: bool = False,
    current_user: dict = Depends(get_current_user)
):
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        logger.warning(f"Upload failed: file too large ({len(contents)} bytes) by {current_user['username']}")
        raise HTTPException(status_code=413, detail="File too large (max 2MB)")

    kind = filetype.guess(contents)
    if not kind or kind.mime not in ["image/jpeg", "image/png"]:
        logger.warning(f"Upload failed: invalid file type '{kind.mime if kind else 'unknown'}' by {current_user['username']}")
        raise HTTPException(status_code=400, detail="Only JPEG/PNG images allowed")
    
    if encrypt:
        encrypted_data = cipher.encrypt(contents)
        file_to_save = encrypted_data
    else:
        file_to_save = contents
        
    ext = ".bin"
    new_filename = str(uuid.uuid4()) + ext
    file_path = os.path.join("storage", new_filename)

    with open(file_path, "wb") as f:
        f.write(file_to_save)

    new_id = max([f["id"] for f in files_db], default=0) + 1
    files_db.append({
        "id": new_id,
        "name": file.filename,
        "owner": current_user["username"],
        "path": file_path,
        "size": len(contents),
        "is_encrypted": encrypt
    })
    
    logger.info(f"File uploaded: {file.filename} (id={new_id}) by {current_user['username']}, encrypted={encrypt}")
    return {"msg": "File uploaded", "file_id": new_id, "encrypted": encrypt}

@app.get("/files/{file_id}/download")
async def download_file(
    file_id: int,
    current_user: dict = Depends(get_current_user)
):
    file_meta = next((f for f in files_db if f["id"] == file_id), None)
    if not file_meta:
        raise HTTPException(status_code=404, detail="Not found")
    if current_user["role"] != "admin" and file_meta["owner"] != current_user["username"]:
        logger.warning(f"IDOR attempt: {current_user['username']} tried to download file {file_id} owned by {file_meta['owner']}")
        raise HTTPException(status_code=404, detail="Not found")

    if not os.path.exists(file_meta["path"]):
        raise HTTPException(status_code=404, detail="File not found on server")

    with open(file_meta["path"], "rb") as f:
        file_data = f.read()

    if file_meta.get("is_encrypted", False):
        try:
            file_data = cipher.decrypt(file_data)
        except Exception:
            logger.error(f"Decryption failed for file {file_id} by {current_user['username']}")
            raise HTTPException(status_code=500, detail="Decryption failed")

        logger.info(f"File downloaded (encrypted): {file_meta['name']} (id={file_id}) by {current_user['username']}")
        return Response(content=file_data, media_type="application/octet-stream", headers={"Content-Disposition": f"attachment; filename={file_meta['name']}"})
    else:
        logger.info(f"File downloaded: {file_meta['name']} (id={file_id}) by {current_user['username']}")
        return FileResponse(
            path=file_meta["path"],
            filename=file_meta["name"],
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={file_meta['name']}"}
        )
        
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"detail": "We are sorry, something went wrong."}
    )

@app.get("/cause_error")
async def cause_error():
    return 1 / 0
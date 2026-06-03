from fastapi import FastAPI, Request, Form, Header
from fastapi.templating import Jinja2Templates
from .schemas import UserCreate
import bleach
from markupsafe import Markup

app = FastAPI()
templates = Jinja2Templates(directory="templates")
templates.env.cache = {}

comments_db = []

users_db = [
    {"id": 1, "username": "alice", "role": "user"},
    {"id": 2, "username": "bob", "role": "user"},
    {"id": 3, "username": "admin", "role": "admin"},
]

files_db = [
    {"id": 1, "name": "alice_report.txt", "owner": "alice", "size": "1024"},
    {"id": 2, "name": "bob_report.txt", "owner": "bob", "size": "2048"},
    {"id": 3, "name": "admin_report.txt", "owner": "admin", "size": "512"},
]

from fastapi import Depends, HTTPException

def get_current_user(username: str = Header(default="admin")):
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
    return Markup(cleaned)

@app.get("/files/{file_id}")
def get_file(file: dict = Depends(check_file_permissions)):
    return {"id": file["id"], "name": file["name"], "owner": file["owner"], "size": file["size"]}

@app.delete("/files/{file_id}")
def delete_file(file_id: int, current_user: dict = Depends(get_current_user)):
    file = next((f for f in files_db if f["id"] == file_id), None)
    if not file:
        raise HTTPException(status_code=404, detail="Not found")
    if current_user["role"] != "admin" and file["owner"] != current_user["username"]:
        raise HTTPException(status_code=404, detail="Not found")
    files_db.remove(file)
    return {"msg": "File deleted"}

@app.get("/files/my")
def get_my_files(current_user: dict = Depends(get_current_user)):
    my_files = [f for f in files_db if f["owner"] == current_user["username"]]
    return {"files": my_files}

@app.get("/files/all")
def get_all_files(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    return {"files": files_db}

@app.post("/registration")
async def registration(user: UserCreate):
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
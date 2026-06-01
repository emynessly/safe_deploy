from fastapi import FastAPI, Request, Form
from fastapi.templating import Jinja2Templates
from .schemas import UserCreate
import bleach
from markupsafe import Markup

app = FastAPI()
templates = Jinja2Templates(directory="templates")
templates.env.cache = {}

comments_db = []

ALLOWED_TAGS = ['b', 'i', 'u', 'em', 'strong']

def clean_text(text: str) -> str:
    cleaned = bleach.clean(text, tags=ALLOWED_TAGS, strip=True)
    return Markup(cleaned)

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
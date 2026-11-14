from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase, relationship
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pwdlib import PasswordHash
from dotenv import load_dotenv
import uvicorn
import secrets
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)
    print("WARNING: SECRET_KEY is not set. Logins will reset on every restart.")

IS_PRODUCTION = os.getenv("RENDER") is not None

# DB
dataBaseURL = os.getenv("DATABASE_URL", "sqlite:///todos.db")

# SQL
if dataBaseURL.startswith("postgres://"):
    dataBaseURL = dataBaseURL.replace("postgres://", "postgresql+psycopg://", 1)
elif dataBaseURL.startswith("postgresql://"):
    dataBaseURL = dataBaseURL.replace("postgresql://", "postgresql+psycopg://", 1)

if dataBaseURL.startswith("sqlite"):
    engine = create_engine(dataBaseURL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(dataBaseURL, pool_pre_ping=True)

sessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class base(DeclarativeBase):
    pass


class User(base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    passwordHash = Column(String(255), nullable=False)
    userNotes = Column(String(250), nullable=True)

    # One user has many todos. Deleting a user deletes their todos too.
    todos = relationship("TodoItem", back_populates="owner", cascade="all, delete-orphan")


class TodoItem(base):
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String(200), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    owner = relationship("User", back_populates="todos")


base.metadata.create_all(engine)

passwordHasher = PasswordHash.recommended()


# Data Shapes
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    username: str
    password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    userNotes: Optional[str] = None


class TodoCreate(BaseModel):
    text: str = Field(max_length=200)


class TodoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str


class NotesUpdate(BaseModel):
    userNotes: str = Field(max_length=250)


# helping funcs
def get_db():
    db = sessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Looks at the login cookie and returns the logged-in User, or sends a 401."""
    userId = request.session.get("user_id")
    if userId is None:
        raise HTTPException(status_code=401, detail="Not logged in.")

    user = db.get(User, userId)
    if user is None:  
        request.session.clear()
        raise HTTPException(status_code=401, detail="Not logged in.")
    return user


# API
app = FastAPI(title="TODO List API with Users")

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    same_site="lax",     
    https_only=IS_PRODUCTION,  
    max_age=14 * 24 * 60 * 60, 
)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def root():
    return FileResponse("static/index.html")


# endpoint
@app.post("/signup", response_model=UserRead)
def signup(data: UserCreate, request: Request, db: Session = Depends(get_db)):
    username = data.username.strip().lower()
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters.")

    newUser = User(username=username, passwordHash=passwordHasher.hash(data.password))
    db.add(newUser)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="That username is already taken.")

    db.refresh(newUser)
    request.session["user_id"] = newUser.id 
    return newUser


@app.post("/login", response_model=UserRead)
def login(data: UserLogin, request: Request, db: Session = Depends(get_db)):
    username = data.username.strip().lower()
    user = db.query(User).filter(User.username == username).first()

    if user is None or not passwordHasher.verify(data.password, user.passwordHash):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    request.session["user_id"] = user.id
    return user


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"message": "Logged out."}


@app.get("/me", response_model=Optional[UserRead])
def me(request: Request, db: Session = Depends(get_db)):
    userId = request.session.get("user_id")
    if userId is None:
        return None
    return db.get(User, userId)

@app.get("/todos", response_model=List[TodoRead])
def view_list(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(TodoItem).filter(TodoItem.user_id == user.id).all()


@app.post("/todos", response_model=TodoRead)
def add_item(item: TodoCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    text = item.text.strip()
    if text == "":
        raise HTTPException(status_code=400, detail="Todo text can't be empty.")

    newItem = TodoItem(text=text, user_id=user.id)
    db.add(newItem)
    db.commit()
    db.refresh(newItem)
    return newItem


@app.delete("/todos/{item_id}")
def complete_item(item_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = db.query(TodoItem).filter(
        TodoItem.id == item_id,
        TodoItem.user_id == user.id,
    ).first()

    if item is None:
        raise HTTPException(status_code=404, detail="Invalid item id.")

    removedText = item.text
    db.delete(item)
    db.commit()
    return {"message": f"Item {item_id} ({removedText}) has been marked as complete and removed."}


@app.put("/me/notes", response_model=UserRead)
def update_notes(data: NotesUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    user.userNotes = data.userNotes.strip()
    db.commit()
    db.refresh(user)
    return user


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

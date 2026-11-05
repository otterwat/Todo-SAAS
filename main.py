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

# ---------- Settings ----------
# SECRET_KEY signs the login cookie so nobody can fake it.
# Set it as an environment variable (in .env locally, in Render's dashboard online).
# If it's missing we make a random one, which is safe, but everyone gets logged
# out each time the server restarts.
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)
    print("WARNING: SECRET_KEY is not set. Logins will reset on every restart.")

# Render sets a variable called RENDER automatically. When online (https),
# we tell the browser to only send the login cookie over secure connections.
IS_PRODUCTION = os.getenv("RENDER") is not None

# ---------- Database setup ----------
dataBaseURL = os.getenv("DATABASE_URL", "sqlite:///todos.db")

# Make sure SQLAlchemy uses the psycopg (version 3) driver for Postgres
if dataBaseURL.startswith("postgres://"):
    dataBaseURL = dataBaseURL.replace("postgres://", "postgresql+psycopg://", 1)
elif dataBaseURL.startswith("postgresql://"):
    dataBaseURL = dataBaseURL.replace("postgresql://", "postgresql+psycopg://", 1)

if dataBaseURL.startswith("sqlite"):
    # check_same_thread is a SQLite-only setting
    engine = create_engine(dataBaseURL, connect_args={"check_same_thread": False})
else:
    # pool_pre_ping tests a connection before using it, which helps
    # when a free database has gone idle and dropped the connection
    engine = create_engine(dataBaseURL, pool_pre_ping=True)

sessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class base(DeclarativeBase):
    pass


class User(base):  # database table
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    # We store a HASH of the password, never the password itself.
    passwordHash = Column(String(255), nullable=False)

    # One user has many todos. Deleting a user deletes their todos too.
    todos = relationship("TodoItem", back_populates="owner", cascade="all, delete-orphan")


class TodoItem(base):  # database table
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String(200), index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    owner = relationship("User", back_populates="todos")


base.metadata.create_all(engine)  # creates tables that don't exist yet


# ---------- Password hashing ----------
passwordHasher = PasswordHash.recommended()  # uses Argon2, a modern hashing method


# ---------- Data shapes (what the API accepts and returns) ----------
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    username: str
    password: str


class UserRead(BaseModel):
    # Notice: no password in here. We never send it back.
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str


class TodoCreate(BaseModel):
    text: str = Field(max_length=200)
    # Notice: no user_id. The server decides who you are from your login cookie,
    # because anything the browser sends could be faked.


class TodoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str


# ---------- Helpers ----------
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
    if user is None:  # the account was deleted but the cookie is still around
        request.session.clear()
        raise HTTPException(status_code=401, detail="Not logged in.")
    return user


# ---------- API ----------
app = FastAPI(title="TODO List API with Users")

# Gives every visitor a signed cookie we can store their user id in.
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    same_site="lax",           # blocks the cookie on most cross-site requests
    https_only=IS_PRODUCTION,  # secure cookies when online
    max_age=14 * 24 * 60 * 60, # stay logged in for 14 days
)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def root():
    return FileResponse("static/index.html")


# --- Account endpoints ---
@app.post("/signup", response_model=UserRead)
def signup(data: UserCreate, request: Request, db: Session = Depends(get_db)):
    username = data.username.strip().lower()  # "Bob" and "bob" count as the same name
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters.")

    newUser = User(username=username, passwordHash=passwordHasher.hash(data.password))
    db.add(newUser)
    try:
        db.commit()
    except IntegrityError:  # the unique rule on username was broken
        db.rollback()
        raise HTTPException(status_code=409, detail="That username is already taken.")

    db.refresh(newUser)
    request.session["user_id"] = newUser.id  # log them in right away
    return newUser


@app.post("/login", response_model=UserRead)
def login(data: UserLogin, request: Request, db: Session = Depends(get_db)):
    username = data.username.strip().lower()
    user = db.query(User).filter(User.username == username).first()

    # Same message for "no such user" and "wrong password", so attackers
    # can't use this to find out which usernames exist.
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
        return None          # not logged in: a normal answer, not an error
    return db.get(User, userId)


# --- Todo endpoints (all require login) ---
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
    db.refresh(newItem)  # loads the id the database just assigned
    return newItem


@app.delete("/todos/{item_id}")
def complete_item(item_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # Look for the item only among THIS user's todos. Otherwise anyone
    # logged in could delete other people's items by guessing ids.
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


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

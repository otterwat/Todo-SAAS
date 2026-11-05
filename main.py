from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, ConfigDict
from typing import List
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

# ---------- Database setup ----------
dataBaseURL = "sqlite:///todos.db"
engine = create_engine(dataBaseURL, connect_args={"check_same_thread": False})
sessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
base = declarative_base()


class TodoItem(base):  # database table
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String(200), index=True)


base.metadata.create_all(engine)  # creates the table if it doesn't exist


# ---------- Data shapes (what the API accepts and returns) ----------
class TodoCreate(BaseModel):
    text: str


class TodoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str


# ---------- Database session helper ----------
def get_db():
    db = sessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- API ----------
app = FastAPI(title="TODO List API")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return FileResponse("static/index.html")


@app.get("/todos", response_model=List[TodoRead])
def view_list(db: Session = Depends(get_db)):
    return db.query(TodoItem).all()


@app.post("/todos", response_model=TodoRead)
def add_item(item: TodoCreate, db: Session = Depends(get_db)):
    newItem = TodoItem(text=item.text.strip())
    db.add(newItem)
    db.commit()
    db.refresh(newItem)  # loads the id the database just assigned
    return newItem


@app.delete("/todos/{item_id}")
def complete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(TodoItem).filter(TodoItem.id == item_id).first()

    if item is None:
        raise HTTPException(status_code=404, detail="Invalid item id.")

    removedText = item.text
    db.delete(item)
    db.commit()
    return {"message": f"Item {item_id} ({removedText}) has been marked as complete and removed."}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
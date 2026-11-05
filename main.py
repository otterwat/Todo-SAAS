from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, session
from sqlalchemy.ext.declarative import declarative_base


dataBaseURL = ("sqlite:///todos.db")
engine = create_engine(dataBaseURL, connect_args={"check_same_thread": False})
sessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI(title="TODO List API")

todoList = []


class TodoItem(Base):
	__tablename__ = "todos"

	id = Column(Integer, primary_key=True, index=True)
	text = Column(String(200), index=True)

Base.metadata.create_all(engine)

class TodoCreate(BaseModel):
	text: str

class TodoRead(BaseModel):
	id: int
	text: str

@app.get("/")
def root():
	return {
		"message": "Welcome to TODO!"
	}


@app.get("/todos")
def view_list():
	return {"todos": todoList}


@app.post("/todos")
def add_item(item: TodoItem):
	todoList.append(item.text.strip())
	return {
		"message": f"'{item.text.strip()}' has been added to your TODO list.",
		"todos": todoList,
	}


@app.delete("/todos/{item_number}")
def complete_item(item_number: int):
	if item_number < 1 or item_number > len(todoList):
		raise HTTPException(status_code=404, detail="Invalid item number.")

	removed = todoList.pop(item_number - 1)
	return {
		"message": f"Item {item_number} ({removed}) has been marked as complete and removed.",
		"todos": todoList,
	}
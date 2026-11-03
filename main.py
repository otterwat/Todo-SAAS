from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()
todoList = []

class TodoItem(BaseModel):
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
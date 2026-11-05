// The address of your API. A relative URL works because FastAPI serves this page too.
const API_URL = "/todos";

// Grab the HTML elements we need to work with
const listEl = document.getElementById("todo-list");
const form = document.getElementById("add-form");
const input = document.getElementById("todo-input");
const message = document.getElementById("message");

// ---------- VIEW: GET /todos ----------
async function loadTodos() {
  try {
    const response = await fetch(API_URL);          // ask the server for the list
    const todos = await response.json();            // turn the reply into a JS array

    listEl.innerHTML = "";                          // clear the old list
    message.textContent = "";

    if (todos.length === 0) {
      message.textContent = "Nothing to do. Add something!";
    }

    for (const todo of todos) {
      const li = document.createElement("li");

      const span = document.createElement("span");
      span.textContent = todo.text;                 // textContent is safe against HTML injection

      const button = document.createElement("button");
      button.textContent = "Complete";
      button.addEventListener("click", () => completeTodo(todo.id));

      li.append(span, button);
      listEl.appendChild(li);
    }
  } catch (error) {
    message.textContent = "Could not reach the server.";
  }
}

// ---------- ADD: POST /todos ----------
async function addTodo(text) {
  try {
    await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },   // tells the server we're sending JSON
      body: JSON.stringify({ text: text })               // matches your TodoCreate model
    });
    loadTodos();                                         // refresh the list
  } catch (error) {
    message.textContent = "Could not add the item.";
  }
}

// ---------- COMPLETE: DELETE /todos/{id} ----------
async function completeTodo(id) {
  try {
    await fetch(`${API_URL}/${id}`, { method: "DELETE" });
    loadTodos();
  } catch (error) {
    message.textContent = "Could not complete the item.";
  }
}

// Runs when the form is submitted (button click or pressing Enter)
form.addEventListener("submit", (event) => {
  event.preventDefault();          // stop the browser from reloading the page
  const text = input.value.trim();
  if (text === "") return;
  addTodo(text);
  input.value = "";                // clear the box
});

// Load the list as soon as the page opens
loadTodos();

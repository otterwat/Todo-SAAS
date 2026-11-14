// HTML elements
const authView = document.getElementById("auth-view");
const todoView = document.getElementById("todo-view");

const tabLogin = document.getElementById("tab-login");
const tabSignup = document.getElementById("tab-signup");
const loginForm = document.getElementById("login-form");
const signupForm = document.getElementById("signup-form");
const loginButton = document.querySelector('#login-form button[type="submit"]');
const signupButton = document.querySelector('#signup-form button[type="submit"]');
const authMessage = document.getElementById("auth-message");

const currentUser = document.getElementById("current-user");
const logoutButton = document.getElementById("logout-button");

const listEl = document.getElementById("todo-list");
const addForm = document.getElementById("add-form");
const addButton = document.querySelector('#add-form button[type="submit"]');
const todoInput = document.getElementById("todo-input");
const message = document.getElementById("message");

const notesInput = document.getElementById("notes-input");
const notesSave = document.getElementById("notes-save");
const notesStatus = document.getElementById("notes-status");

// ---------- Load the sound effects ---------- //
const selectAudio = new Audio("/static/assets/select.mp3");
const confettiAudio = new Audio("/static/assets/confetti.mp3");

// ---------- Helpers ---------- //
async function api(url, method = "GET", body = null) {
  const options = { method: method, headers: {} };
  if (body !== null) {
	options.headers["Content-Type"] = "application/json";
	options.body = JSON.stringify(body);
  }

  const response = await fetch(url, options);  

  if (response.status === 401 && url !== "/login") {
	showAuthView();
	throw new Error("Please log in.");
  }

  let data = null;
  try {
	data = await response.json();
  } catch (e) {
	// no JSON body
  }

  if (!response.ok) {
	throw new Error(readError(data));
  }
  return data;
}

function readError(data) {
  if (data && typeof data.detail === "string") {
	return data.detail;
  }
  if (data && Array.isArray(data.detail) && data.detail.length > 0) {
	const first = data.detail[0];
	const field = first.loc ? first.loc[first.loc.length - 1] : "input";
	return `Problem with ${field}: ${first.msg}`;
	}
	return "Something went wrong.";

}

// Plays sounds //
function playSound(sound) {
	sound.currentTime = 0;
	sound.play().catch(() => { });
}

// view swithing
function showAuthView() {
  todoView.hidden = true;
  authView.hidden = false;
}

function showTodoView(user) {
	authView.hidden = true;
	todoView.hidden = false;
	currentUser.textContent = user.username;
	notesInput.value = user.userNotes || "";
	notesStatus.textContent = "";
	loadTodos();
}

function showTab(which) {
  const isLogin = which === "login";
  loginForm.hidden = !isLogin;
  signupForm.hidden = isLogin;
  tabLogin.classList.toggle("active", isLogin);
  tabSignup.classList.toggle("active", !isLogin);
  authMessage.textContent = "";
}

tabLogin.addEventListener("click", () => { playSound(selectAudio); showTab("login"); });
tabSignup.addEventListener("click", () => { playSound(selectAudio); showTab("signup"); });
loginButton.addEventListener("click", () => { playSound(selectAudio); });
signupButton.addEventListener("click", () => { playSound(selectAudio); });
addButton.addEventListener("click", () => { playSound(selectAudio); });



// Sign up
signupForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  authMessage.textContent = "";
  try {
	const user = await api("/signup", "POST", {
	  username: document.getElementById("signup-username").value,
	  password: document.getElementById("signup-password").value,
	});
	signupForm.reset();
	showTodoView(user);          // signing up also logs you in
  } catch (error) {
	authMessage.textContent = error.message;
  }
});


// log in
loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  authMessage.textContent = "";
  try {
	const user = await api("/login", "POST", {
	  username: document.getElementById("login-username").value,
	  password: document.getElementById("login-password").value,
	});
	loginForm.reset();
	showTodoView(user);
  } catch (error) {
	authMessage.textContent = error.message;
  }
});


// log out
logoutButton.addEventListener("click", async () => {
  try {
	await api("/logout", "POST");
  } catch (error) {
	// even if this fails, show the login screen
  }
  listEl.innerHTML = "";
	notesInput.value = "";
  notesStatus.textContent = "";      
  showTab("login");
  showAuthView();
});

// notes
notesSave.addEventListener("click", async () => {
	notesStatus.textContent = "Saving...";
	try {
		await api("/me/notes", "PUT", { userNotes: notesInput.value });
		notesStatus.textContent = "Saved!";
	} catch (error) {
		notesStatus.textContent = error.message;
	}
});

// todos
async function loadTodos() {
  try {
	const todos = await api("/todos");
	listEl.innerHTML = "";
	message.textContent = "";

	if (todos.length === 0) {
	  message.textContent = "Nothing to do. Add something!";
	}

	for (const todo of todos) {
	  const li = document.createElement("li");

	  const span = document.createElement("span");
	  span.textContent = todo.text;

	  const button = document.createElement("button");
	  button.textContent = "Complete";
	  button.addEventListener("click", () => completeTodo(todo.id));

	  li.append(span, button);
	  listEl.appendChild(li);
	}
  } catch (error) {
	message.textContent = error.message;
  }
}

async function addTodo(text) {
  try {
	await api("/todos", "POST", { text: text });
	loadTodos();
  } catch (error) {
	message.textContent = error.message;
  }
}

async function completeTodo(id) {
  try {
	await api(`/todos/${id}`, "DELETE");
	playSound(confettiAudio);
	confetti();
	loadTodos();
  } catch (error) {
	message.textContent = error.message;
  }
}

addForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = todoInput.value.trim();
  if (text === "") return;
  addTodo(text);
  todoInput.value = "";
});


// check if logged in already
async function start() {
	try {
		const user = await api("/me");
		if (user) {
			showTodoView(user);
		} else {
			showAuthView();
		}
	} catch (error) {
		showAuthView();
	}
}

start();

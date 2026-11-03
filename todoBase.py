todoList = []

def viewList():
	print ("Your TODO list is: ")
	for item in todoList:
		print (f"{item}")

def completeItem():
	item = input("Enter the item you want to mark as complete (the number): ")
	
	if int(item) <= len(todoList):
		print (f"Item {item} ({todoList[int(item)-1]}) has been marked as complete and removed from your TODO list. \n Your list is now: ")
		todoList.remove(todoList[int(item)-1])
		for item in todoList:
			print(f"{item}")
	else:
		print ("Invalid item number. Please try again.")

def addItem():
	item = input("Enter the item you want to add: ")
	todoList.append(item.strip())
	print (f"{item} has been added to your TODO list. \n Your list is now: ")
	for item in todoList:
			print(f"{item}")

print ("welcome to TODO!")

while True:
	action = input ("What do you want to do? (view, add, complete, leave): ")

	match action:
		case "view":
			viewList()

		case "add":
			addItem()

		case "complete":
			completeItem()

		case "leave":
			print ("Thank you for using TODO! Goodbye!")
			exit()

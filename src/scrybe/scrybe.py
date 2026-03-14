from textual.app import App, ComposeResult, Binding
from textual.screen import Screen
from textual.widgets import LoadingIndicator, Button, Input, Header, Footer, MarkdownViewer, ListView, ListItem, TextArea, Markdown, Tabs, Label
from textual.containers import Vertical, Horizontal

from mysql.connector.errors import DatabaseError
from mysql.connector.aio import connect, MySQLConnectionAbstract

from typing import TypedDict

global DATABASE

DATABASE_NAME = "scrybe_db"

LOGIN_INFO = {
	"username": "",
	"password": "",
	"host": ""
}

async def setup_database(connector: MySQLConnectionAbstract) -> None:
	cursor = await connector.cursor()
	await cursor.execute("SHOW DATABASES")
	results = await cursor.fetchall()
	for row in results:
		if row[0] == DATABASE_NAME:
			return

	await cursor.execute(f"CREATE DATABASE {DATABASE_NAME}")
	await cursor.execute(f"USE {DATABASE_NAME}")
	await cursor.execute("CREATE TABLE workspace (workspace_id INT AUTO_INCREMENT, workspace_name VARCHAR(64) NOT NULL UNIQUE, PRIMARY KEY (workspace_id))")
	await cursor.execute("CREATE TABLE page (page_id INT AUTO_INCREMENT, workspace_id INT, page_name VARCHAR(64) NOT NULL, content text, PRIMARY KEY (page_id), FOREIGN KEY (workspace_id) REFERENCES workspace(workspace_id))")

	await connector.commit()
	await cursor.close()

async def create_page(connector: MySQLConnectionAbstract, page_name: str, workspace_name: str) -> int:
	cursor = await connector.cursor()
	await cursor.execute(f"USE {DATABASE_NAME}")
	await cursor.execute("SELECT workspace_id FROM workspace WHERE workspace_name = %s", (workspace_name,))
	
	results = await cursor.fetchall()
	workspace_id = -1
	if len(results) == 1 and len(results[0]) == 1:
		workspace_id = results[0][0]
	else:
		raise Exception(f"No workspace with name '{workspace_name}' exists!")

	await cursor.execute("INSERT INTO page (workspace_id, page_name) values (%s, %s)", (workspace_id, page_name,))
	page_id = cursor.lastrowid

	await connector.commit()
	await cursor.close()

	return page_id

async def get_page_content(connector: MySQLConnectionAbstract, page_id: int) -> str:
	cursor = await connector.cursor()
	await cursor.execute(f"USE {DATABASE_NAME}")
	await cursor.execute("SELECT content FROM page WHERE page_id = %s", (page_id,))
	
	results = await cursor.fetchall()
	if len(results) != 1 and len(results[0]) != 1:
		raise Exception(f"No page with id #{page_id} exists!")
	
	await cursor.close()

	return results[0][0]

class Page(TypedDict):
	page_id: int
	page_name: str

async def get_pages(connector: MySQLConnectionAbstract, workspace_name: str) -> list[Page]:
	cursor = await connector.cursor()
	await cursor.execute(f"USE {DATABASE_NAME}")
	await cursor.execute("SELECT workspace_id FROM workspace WHERE workspace_name = %s", (workspace_name,))
	
	results = await cursor.fetchall()
	workspace_id = -1
	if len(results) == 1 and len(results[0]) == 1:
		workspace_id = results[0][0]
	else:
		raise Exception(f"No workspace with name '{workspace_name}' exists!")
	
	await cursor.execute("SELECT page_id, page_name FROM page WHERE workspace_id = %s", (workspace_id,))
	results = await cursor.fetchall()
	await cursor.close()

	r_list = [{"page_id" : x[0], "page_name" : x[1]} for x in results]
	return r_list

async def create_workspace(connector: MySQLConnectionAbstract, workspace_name: str) -> int:
	cursor = await connector.cursor()
	await cursor.execute(f"USE {DATABASE_NAME}")

	await cursor.execute("SELECT * FROM workspace WHERE workspace_name = %s", (workspace_name,))
	results = await cursor.fetchall()
	if len(results) > 0:
		raise Exception(f"Workspace with name '{workspace_name}' already exists!")

	await cursor.execute("INSERT INTO workspace (workspace_name) values (%s)", (workspace_name,))
	workspace_id = cursor.lastrowid

	await connector.commit()
	await cursor.close()

	return workspace_id

async def get_workspaces(connector: MySQLConnectionAbstract) -> list[str]:
	cursor = await connector.cursor()
	await cursor.execute(f"USE {DATABASE_NAME}")

	await cursor.execute("SELECT workspace_name FROM workspace")
	results = await cursor.fetchall()

	await cursor.close()
	
	return [x[0] for x in results]

class LoginScreen(Screen):
	def compose(self) -> ComposeResult:
		with Vertical(id="loginScreen-container"):
			yield Input(placeholder="Host", id="loginScreen-hostInput")
			yield Input(placeholder="Username", id="loginScreen-usernameInput")
			yield Input(placeholder="Password", id="loginScreen-passwordInput")
			yield Button(label="Login", variant="success", id="loginScreen-loginButton")
		yield LoadingIndicator(id="loginScreen-loading")

	def on_mount(self) -> None:
		loadingIndicator = self.query_one("#loginScreen-loading")
		loadingIndicator.styles.display = "none"

	def on_input_changed(self, event: Input.Changed) -> None:
		if event.input.id == "loginScreen-hostInput":
			LOGIN_INFO["host"] = event.value
		elif event.input.id == "loginScreen-usernameInput":
			LOGIN_INFO["username"] = event.value
		elif event.input.id == "loginScreen-passwordInput":
			LOGIN_INFO["password"] = event.value 
	
	async def update_database(self) -> None:
		DATABASE = None
		loadingIndicator = self.query_one("#loginScreen-loading")
		loadingIndicator.styles.display = "block"

		container = self.query_one("#loginScreen-container")
		container.styles.display = "none"

		host = LOGIN_INFO["host"]
		username = LOGIN_INFO["username"]
		password = LOGIN_INFO["password"]

		if len(host) == 0:
			self.notify("Host cannot be blank.", title="Invalid Input.", severity="warning")
		elif len(username) == 0:
			self.notify("Username cannot be blank.", title="Invalid Input.", severity="warning")
		elif len(password) == 0:
			self.notify("Password cannot be blank.", title="Invalid Input.", severity="warning")
		else:
			try:
				db = await connect(host=host, user=username, password=password)
				await setup_database(db)
				DATABASE = db
				self.notify(f"The connection to the database at {host} was successful.", title="Connection Successful.", severity="information")
			except DatabaseError:
				self.notify(
					"The connection could not be established! Please check your login information.", 
					title="Connection Failure.", 
					severity="error",
					timeout=10
				)
			except ConnectionRefusedError:
				self.notify(
					"The host refused the connection request! Ensure that the host is running a mysql server on port 3306.", 
					title="Connection Failure.", 
					severity="error",
					timeout=10
				)

		loadingIndicator.styles.display = "none"
		container.styles.display = "block"

		if DATABASE:
			self.app.pop_screen()
			self.app.push_screen("editor")

	async def on_button_pressed(self, event: Button.Pressed) -> None:
		if event.button.id == "loginScreen-loginButton":
			self.run_worker(self.update_database(), exclusive=True)

class EditorScreen(Screen):
	BINDINGS = [
		("ctrl+e", "toggle_editor_view", "Show/Hide Editor"),
		("ctrl+n", "new_page", "New Page"),
		("ctrl+r", "reload", "Reload Page"),
	]

	def compose(self) -> ComposeResult:
		yield Header(icon="\U0001FAB6") # U0001FAB6 -> 🪶
		yield Tabs("Workspace 1", "Workspace 2", "Workspace 3")
		with Horizontal(id="editorScreen-container"):
			yield ListView(id="editorScreen-pages")
			yield TextArea(id="editorScreen-textArea", language="markdown", show_line_numbers=True)
			yield MarkdownViewer(id="editorScreen-preview")
		yield Footer()

	def hide_editor(self) -> None:
		text_area = self.query_one("#editorScreen-textArea")
		mdv = self.query_one("#editorScreen-preview")
		text_area.styles.display = "none"
		mdv.styles.display = "none"

	def show_editor(self) -> None:
		text_area = self.query_one("#editorScreen-textArea")
		mdv = self.query_one("#editorScreen-preview")
		text_area.styles.display = "display"
		mdv.styles.display = "display"

	def action_toggle_editor_view(self) -> None:
		text_area = self.query_one("#editorScreen-textArea")
		mdv = self.query_one("#editorScreen-preview")
		if text_area.styles.display == "block":
			text_area.styles.display = "none"
			mdv.styles.width = "80%"
		else:
			text_area.styles.display = "block"
			mdv.styles.width = "40%"
	
	def action_new_page(self) -> None:
		list_view = self.query_one("#editorScreen-pages", ListView)
		list_view.append(ListItem(Label("Untitled Page")))
	
	def on_text_area_changed(self, event: TextArea.Changed) -> None:
		if event.text_area.id == "editorScreen-textArea":
			mdv = self.query_one("#editorScreen-preview")
			md = mdv.query_one(Markdown)
			md.update(event.text_area.text)
	
	def on_mount(self) -> None:
		self.hide_editor()

	def on_list_view_selected(self, event: ListView.Selected) -> None:
		if event.list_view.id == "editorScreen-pages":
			pass

class ScrybeCLI(App):
	SCREENS = {
		"login" : LoginScreen,
		"editor" : EditorScreen
	}
	CSS_PATH = "./styles/scrybe.tcss"

	def on_mount(self):
		self.push_screen("login")

if __name__ == "__main__":
	app = ScrybeCLI()
	app.run()
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import LoadingIndicator, Button, Input, Header, Footer, MarkdownViewer, ListView, TextArea
from textual.containers import Vertical, Horizontal

from mysql.connector.errors import Error as DatabaseError
from mysql.connector.aio import connect, MySQLConnectionAbstract

global DATABASE

DATABASE_NAME = "scrybe_db"

LOGIN_INFO = {
	"username": "",
	"password": "",
	"host": ""
}

async def setup_database(connector: MySQLConnectionAbstract):
	cursor = await connector.cursor()
	await cursor.execute("SHOW DATABASES")
	results = await cursor.fetchall()
	for row in results:
		if row[0] == DATABASE_NAME:
			return

	await cursor.execute(f"CREATE DATABASE {DATABASE_NAME}")
	await cursor.execute(f"USE {DATABASE_NAME}")
	await cursor.execute("CREATE TABLE workspace (workspace_id INT AUTO_INCREMENT, workspace_name VARCHAR(64) NOT NULL, PRIMARY KEY (workspace_id))")
	await cursor.execute("CREATE TABLE page (page_id INT AUTO_INCREMENT, workspace_id INT, page_name VARCHAR(64) NOT NULL, content text, PRIMARY KEY (page_id), FOREIGN KEY (workspace_id) REFERENCES workspace(workspace_id))")

	await connector.commit()
	await cursor.close()

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
			except TypeError:
				self.notify(
					"An unknown error occured! Please check your login information and confirm that the provided host is currently running mysql.", 
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

class Editor(Screen):
	def compose(self) -> ComposeResult:
		yield Header(icon="\U0001FAB6") # U0001FAB6 -> 🪶
		with Horizontal():
			yield ListView()
			yield TextArea()
			yield MarkdownViewer()
		yield Footer()

class ScrybeCLI(App):
	SCREENS = {
		"login" : LoginScreen,
		"editor" : Editor
	}
	CSS_PATH = "./styles/scrybe.tcss"

	def on_mount(self):
		self.push_screen("login")

if __name__ == "__main__":
	app = ScrybeCLI()
	app.run()
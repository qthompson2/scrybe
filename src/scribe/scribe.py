from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import LoadingIndicator, Button, Input, Header, Footer, MarkdownViewer, ListView, TextArea
from textual.containers import Vertical, Horizontal

from mysql.connector.errors import Error as DatabaseError

from async_mysql import AsyncMysqlWrapper

DATABASE = None

LOGIN_INFO = {
	"username": "",
	"password": "",
	"host": ""
}

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
	
	async def on_button_pressed(self, event: Button.Pressed) -> None:
		if event.button.id == "loginScreen-loginButton":
			DATABASE = None
			loadingIndicator = self.query_one("#loginScreen-loading")
			loadingIndicator.styles.display = "block"

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
					async with AsyncMysqlWrapper(host=host, user=username, password=password) as db:
						self.notify(f"The connection to the database @ {host} was successful.", title="Connection Successful.", severity="information")
						DATABASE = db
				except DatabaseError:
					self.notify(
						"An unknown error occured! Please check your login information and confirm that the provided host is currently running mysql.", 
						title="Connection Failure.", 
						severity="error",
						timeout=10
					)

			loadingIndicator = self.query_one("#loginScreen-loading")
			loadingIndicator.styles.display = "none"

			if DATABASE:
				self.app.pop_screen()
				self.app.push_screen("editor")

class Editor(Screen):
	def compose(self) -> ComposeResult:
		yield Header(icon="\U0001FAB6") # U0001FAB6 -> 🪶
		with Horizontal():
			yield ListView()
			yield TextArea()
			yield MarkdownViewer()
		yield Footer()

class ScribeCLI(App):
	SCREENS = {
		"login" : LoginScreen,
		"editor" : Editor
	}
	CSS_PATH = "./styles/scribe.tcss"

	def on_mount(self):
		self.push_screen("login")

if __name__ == "__main__":
	app = ScribeCLI()
	app.run()
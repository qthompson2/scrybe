from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import LoadingIndicator, Button, Input
from textual.containers import Vertical

from mysql.connector.errors import DatabaseError

from .database import Database

class LoginScreen(Screen):
	login_info = {
		"username": "",
		"password": "",
		"host": ""
	}

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
			self.login_info["host"] = event.value
		elif event.input.id == "loginScreen-usernameInput":
			self.login_info["username"] = event.value
		elif event.input.id == "loginScreen-passwordInput":
			self.login_info["password"] = event.value 
	
	async def update_database(self) -> None:
		self.app._db_pool = None
		loadingIndicator = self.query_one("#loginScreen-loading")
		loadingIndicator.styles.display = "block"

		container = self.query_one("#loginScreen-container")
		container.styles.display = "none"

		host = self.login_info["host"]
		username = self.login_info["username"]
		password = self.login_info["password"]

		if len(host) == 0:
			self.notify("Host cannot be blank.", title="Invalid Input ⚠️", severity="warning")
		elif len(username) == 0:
			self.notify("Username cannot be blank.", title="Invalid Input ⚠️", severity="warning")
		elif len(password) == 0:
			self.notify("Password cannot be blank.", title="Invalid Input ⚠️", severity="warning")
		else:
			try:
				async with Database(host, username, password) as new:
					await new.setup()
					self.app.db = new
					self.notify(f"The connection to the database at {host} was successful.", title="Connection Successful ✅", severity="information")
			except DatabaseError:
				self.notify(
					"The connection could not be established! Please check your login information.", 
					title="Connection Failure ❌", 
					severity="error",
					timeout=10
				)
			except ConnectionRefusedError:
				self.notify(
					"The host refused the connection request! Ensure that the host is running a mysql server on port 3306.", 
					title="Connection Failure ❌", 
					severity="error",
					timeout=10
				)

		loadingIndicator.styles.display = "none"
		container.styles.display = "block"

		if self.app.db:
			self.app.pop_screen()
			self.app.push_screen("editor")

	def on_button_pressed(self, event: Button.Pressed) -> None:
		if event.button.id == "loginScreen-loginButton":
			self.run_worker(self.update_database(), exclusive=True)
from textual.app import App, ComposeResult, Binding
from textual.screen import Screen, ModalScreen
from textual.widgets import LoadingIndicator, Button, Input, Header, Footer, MarkdownViewer, ListView, ListItem, TextArea, Markdown, Tabs, Label
from textual.containers import Vertical, Horizontal

from mysql.connector.errors import DatabaseError
from mysql.connector.aio import connect

from database import setup_database, create_page, create_workspace, get_pages, get_workspaces, get_page_content, delete_workspace

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
	
	async def update_database(self) -> None:
		self.app._database = None
		loadingIndicator = self.query_one("#loginScreen-loading")
		loadingIndicator.styles.display = "block"

		container = self.query_one("#loginScreen-container")
		container.styles.display = "none"

		host = LOGIN_INFO["host"]
		username = LOGIN_INFO["username"]
		password = LOGIN_INFO["password"]

		if len(host) == 0:
			self.notify("Host cannot be blank.", title="Invalid Input ⚠️", severity="warning")
		elif len(username) == 0:
			self.notify("Username cannot be blank.", title="Invalid Input ⚠️", severity="warning")
		elif len(password) == 0:
			self.notify("Password cannot be blank.", title="Invalid Input ⚠️", severity="warning")
		else:
			try:
				db = await connect(host=host, user=username, password=password)
				await setup_database(db)
				self.app._database = db
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

		if self.app._database:
			self.app.pop_screen()
			self.app.push_screen("editor")

	def on_button_pressed(self, event: Button.Pressed) -> None:
		if event.button.id == "loginScreen-loginButton":
			self.run_worker(self.update_database(), exclusive=True)

class NewPageScreen(ModalScreen):
	BINDINGS = [("escape", "app.pop_screen", "Close")]

	def __init__(self, parent: Screen, **kwargs):
		super().__init__(**kwargs)
		self.parent_screen = parent

	def compose(self) -> ComposeResult:
		with Vertical(id="pageScreen-container"):
			yield Input(id="pageScreen-input", placeholder="Page name")
			yield Button(id="pageScreen-confirm", label="Confirm", variant="primary")

	def on_button_pressed(self, event: Button.Pressed) -> None:
		if event.button.id == "pageScreen-confirm":
			inp = self.query_one("#pageScreen-input", Input)
			self.run_worker(self.parent_screen.create_new_page(inp.value))
			self.app.pop_screen()

class NewWorkspaceScreen(ModalScreen):
	BINDINGS = [("escape", "app.pop_screen", "Close")]

	def __init__(self, parent: Screen, **kwargs):
		super().__init__(**kwargs)
		self.parent_screen = parent

	def compose(self) -> ComposeResult:
		with Vertical(id="workspaceScreen-container"):
			yield Input(id="workspaceScreen-input", placeholder="Workspace name")
			yield Button(id="workspaceScreen-confirm", label="Confirm", variant="primary")
	
	def on_button_pressed(self, event: Button.Pressed) -> None:
		if event.button.id == "workspaceScreen-confirm":
			inp = self.query_one("#workspaceScreen-input", Input)
			self.run_worker(self.parent_screen.create_new_workspace(inp.value))
			self.app.pop_screen()

class ConfirmDeleteWorkspace(ModalScreen):
	BINDINGS = [("escape", "app.pop_screen", "Close")]

	def __init__(self, parent: Screen, **kwargs):
		super().__init__(**kwargs)
		self.parent_screen = parent

	def compose(self) -> ComposeResult:
		with Vertical(id="deleteWorkspace-container"):
			yield Label(f"The workspace ({self.parent_screen.current_workspace}) and all of its contents will be deleted.")
			with Horizontal():
				yield Button(id="deleteWorkspace-confirm", label="Delete", variant="error")
				yield Button(id="deleteWorkspace-cancel", label="Cancel", variant="primary")
	
	def on_button_pressed(self, event: Button.Pressed) -> None:
		if event.button.id == "deleteWorkspace-confirm":
			self.run_worker(self.parent_screen.remove_workspace())
			self.app.pop_screen()
		elif event.button.id == "deleteWorkspace-cancel":
			self.app.pop_screen()

class EditorScreen(Screen):
	BINDINGS = [
		("ctrl+e", "toggle_editor_view", "Show/Hide Editor"),
		("ctrl+n", "new_page", "New Page"),
		("ctrl+shift+p", "delete_page", "Delete Page"),
		("ctrl+r", "reload", "Reload Page"),
		("ctrl+w", "new_workspace", "New Workspace"),
		("del+w", "delete_workspace", "Delete Workspace"),
	]

	current_workspace = None
	current_page = None

	def compose(self) -> ComposeResult:
		yield Header(icon="🪶") # U0001FAB6 -> 🪶
		yield Tabs(id="editorScreen-workspaces")
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

	async def create_new_workspace(self, name) -> None:
		try:
			await create_workspace(self.app._database, name)
			workspaces = self.query_one("#editorScreen-workspaces", Tabs)
			workspaces.add_tab(name)
		except Exception as e:
			self.notify(str(e), title="Database Error ⚠️", severity="warning", timeout=10)
	
	async def remove_workspace(self) -> None:
		try:
			await delete_workspace(self.app._database, self.current_workspace)
			await self.update_workspaces()
		except Exception as e:
			self.notify(str(e), title="Database Error ⚠️", severity="warning", timeout=10)

	async def create_new_page(self, name) -> None:
		if self.current_workspace:
			try:
				await create_page(self.app._database, name, self.current_workspace)
				pages = self.query_one("#editorScreen-pages", ListView)
				pages.append(ListItem(Label(name)))
			except Exception as e:
				self.notify(str(e), title="Database Error ⚠️", severity="warning", timeout=10)

	def action_toggle_editor_view(self) -> None:
		if self.current_workspace:
			text_area = self.query_one("#editorScreen-textArea")
			mdv = self.query_one("#editorScreen-preview")
			if text_area.styles.display == "block":
				text_area.styles.display = "none"
				mdv.styles.width = "80%"
			else:
				text_area.styles.display = "block"
				mdv.styles.width = "40%"
	
	def action_new_page(self) -> None:
		self.app.push_screen(NewPageScreen(self))
	
	def action_new_workspace(self) -> None:
		self.app.push_screen(NewWorkspaceScreen(self))
	
	def action_delete_workspace(self) -> None:
		self.app.push_screen(ConfirmDeleteWorkspace(self))
	
	def on_text_area_changed(self, event: TextArea.Changed) -> None:
		if event.text_area.id == "editorScreen-textArea":
			mdv = self.query_one("#editorScreen-preview")
			md = mdv.query_one(Markdown)
			md.update(event.text_area.text)
	
	async def update_workspaces(self) -> None:
		workspace_names = await get_workspaces(self.app._database)
		workspaces = self.query_one("#editorScreen-workspaces", Tabs)
		await workspaces.clear()
		if len(workspace_names) == 0:
			self.current_workspace = None
			self.notify("Create a workspace with ^w to get started.", title="Tips 💡", severity="information", timeout=10)
		else:
			self.current_workspace = workspace_names[0]
			for workspace_name in workspace_names:
				workspaces.add_tab(workspace_name)
			await self.update_pages()
	
	async def update_pages(self) -> None:
		pages = await get_pages(self.app._database, self.current_workspace)
		page_list = self.query_one("#editorScreen-pages", ListView)
		await page_list.clear()
		if len(pages) != 0:
			self.current_page = pages[0]["page_id"]
			for page in pages:
				page_list.append(ListItem(Label(page["page_name"]), id=f"page-{page['page_id']}"))

	def on_mount(self) -> None:
		self.hide_editor()
		self.run_worker(self.update_workspaces(), exclusive=True)

	def on_list_view_selected(self, event: ListView.Selected) -> None:
		if event.list_view.id == "editorScreen-pages":
			self.current_page = int(event.item.id.replace("page-", ""))
	
	def on_tab_activated(self, event: Tabs.TabActivated) -> None:
		self.current_workspace = event.tab.label
		self.run_worker(self.update_pages(), exclusive=True)

class ScrybeCLI(App):
	SCREENS = {
		"login" : LoginScreen,
		"editor" : EditorScreen
	}
	CSS_PATH = "./styles/scrybe.tcss"
	_database = None

	def on_mount(self):
		self.push_screen("login")

if __name__ == "__main__":
	app = ScrybeCLI()
	app.run()
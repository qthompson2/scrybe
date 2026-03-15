from textual.app import ComposeResult
from textual.screen import Screen, ModalScreen
from textual.widgets import Button, Input, Header, Footer, MarkdownViewer, ListView, ListItem, TextArea, Markdown, Tabs, Label, Tab
from textual.containers import Vertical, Horizontal

class CreateNewScreen(ModalScreen):
	BINDINGS = [("escape", "app.pop_screen", "Close")]

	def __init__(self, parent: Screen, **kwargs):
		super().__init__(**kwargs)
		self.parent_screen = parent

	def compose(self) -> ComposeResult:
		with Vertical():
			yield Tabs("Page", "Workspace", id="createNew-tabs")
			with Vertical(id="pageScreen-container"):
				yield Input(id="pageScreen-input", placeholder="Page name")
				yield Button(id="pageScreen-confirm", label="Confirm", variant="primary")
			with Vertical(id="workspaceScreen-container"):
				yield Input(id="workspaceScreen-input", placeholder="Workspace name")
				yield Button(id="workspaceScreen-confirm", label="Confirm", variant="primary")

	def on_button_pressed(self, event: Button.Pressed) -> None:
		if event.button.id == "pageScreen-confirm":
			inp = self.query_one("#pageScreen-input", Input)
			self.parent_screen.run_worker(self.parent_screen.create_new_page(inp.value))
			self.app.pop_screen()
		elif event.button.id == "workspaceScreen-confirm":
			inp = self.query_one("#workspaceScreen-input", Input)
			self.parent_screen.run_worker(self.parent_screen.create_new_workspace(inp.value))
			self.app.pop_screen()

	def on_mount(self) -> None:
		workspace_container = self.query_one("#workspaceScreen-container", Vertical)
		workspace_container.styles.display = "none"
	
	def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
		page_container = self.query_one("#pageScreen-container", Vertical)
		workspace_container = self.query_one("#workspaceScreen-container", Vertical)
		if event.tab.label == "Page":
			page_container.styles.display = "block"
			workspace_container.styles.display = "none"
		elif event.tab.label == "Workspace":
			page_container.styles.display = "none"
			workspace_container.styles.display = "block"

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
			self.parent_screen.run_worker(self.parent_screen.remove_workspace())
			self.app.pop_screen()
		elif event.button.id == "deleteWorkspace-cancel":
			self.app.pop_screen()

class EditorScreen(Screen):
	BINDINGS = [
		("ctrl+e", "toggle_editor_view", "Show/Hide Editor"),
		("ctrl+n", "new", "New..."),
		("ctrl+d+p", "delete_page", "Delete Page"),
		("ctrl+r", "reload", "Reload Page"),
		("ctrl+w", "new_workspace", "New Workspace"),
		("ctrl+d+w", "delete_workspace", "Delete Workspace"),
	]

	current_workspace = None
	current_page = None
	editor_hidden = False

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
		self.editor_hidden = True

	def show_editor(self) -> None:
		text_area = self.query_one("#editorScreen-textArea")
		mdv = self.query_one("#editorScreen-preview")
		text_area.styles.display = "block"
		mdv.styles.display = "block"
		self.editor_hidden = False

	async def create_new_workspace(self, name) -> None:
		try:
			await self.app.db.create_workspace(name)
			workspaces = self.query_one("#editorScreen-workspaces", Tabs)
			workspaces.add_tab(name)
			if self.current_workspace == None:
				self.current_workspace = name
		except Exception as e:
			self.notify(str(e), title="Database Error ⚠️", severity="warning", timeout=10)
	
	async def remove_workspace(self) -> None:
		try:
			await self.app.db.delete_workspace(self.current_workspace)
			await self.update_workspaces()
		except Exception as e:
				self.notify(str(e), title="Database Error ⚠️", severity="warning", timeout=10)

	async def create_new_page(self, name) -> None:
		if self.current_workspace:
			try:
				page_id = await self.app.db.create_page(name, self.current_workspace)
				pages = self.query_one("#editorScreen-pages", ListView)
				pages.append(ListItem(Label(name), name=f"page-{page_id}"))
			except Exception as e:
				self.notify(str(e), title="Database Error ⚠️", severity="warning", timeout=10)
				raise e

	def action_toggle_editor_view(self) -> None:
		if not self.editor_hidden:
			text_area = self.query_one("#editorScreen-textArea")
			mdv = self.query_one("#editorScreen-preview")
			if text_area.styles.display == "block":
				text_area.styles.display = "none"
				mdv.styles.width = "80%"
			else:
				text_area.styles.display = "block"
				mdv.styles.width = "40%"
	
	def action_new(self) -> None:
		self.app.push_screen(CreateNewScreen(self))
	
	def action_delete_workspace(self) -> None:
		self.app.push_screen(ConfirmDeleteWorkspace(self))
	
	def on_text_area_changed(self, event: TextArea.Changed) -> None:
		if event.text_area.id == "editorScreen-textArea":
			mdv = self.query_one("#editorScreen-preview")
			md = mdv.query_one(Markdown)
			md.update(event.text_area.text)
	
	async def update_workspaces(self) -> None:
		workspace_names = await self.app.db.get_workspaces()
		workspaces = self.query_one("#editorScreen-workspaces", Tabs)
		await workspaces.clear()
		if len(workspace_names) == 0:
			self.current_workspace = None
			self.notify("Create a workspace with ^n to get started.", title="Tips 💡", severity="information", timeout=10)
		else:
			for workspace_name in workspace_names:
				workspaces.add_tab(Tab(workspace_name))
			self.current_workspace = workspace_names[0]
	
	async def update_pages(self) -> None:
		pages = await self.app.db.get_pages(self.current_workspace)
		page_list = self.query_one("#editorScreen-pages", ListView)
		await page_list.clear()
		if len(pages) != 0:
			self.current_page = pages[0]["page_id"]
			for page in pages:
				page_list.append(ListItem(Label(page["page_name"]), name=f"page-{page['page_id']}"))

	def on_mount(self) -> None:
		self.hide_editor()
		self.run_worker(self.update_workspaces(), exclusive=True)

	def on_list_view_selected(self, event: ListView.Selected) -> None:
		if event.list_view.id == "editorScreen-pages":
			self.current_page = int(event.item.name.replace("page-", ""))
			self.show_editor()
			text_area = self.query_one("#editorScreen-textArea", TextArea)
			mdv = self.query_one("#editorScreen-preview", MarkdownViewer)
			md = mdv.query_one(Markdown)
			md.update(text_area.text)
	
	def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
		self.current_workspace = event.tab.label_text
		self.run_worker(self.update_pages(), exclusive=True)
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

class ConfirmDelete(ModalScreen):
	BINDINGS = [("escape", "app.pop_screen", "Close")]

	def __init__(self, parent: Screen, **kwargs):
		super().__init__(**kwargs)
		self.parent_screen = parent
		self.wksp_selected = type(parent.current_workspace) == str
		self.page_selected = type(parent.current_page) == int

		self.tabs = []
		if self.wksp_selected and self.page_selected:
			self.tabs = ["Page", "Workspace"]
		elif self.wksp_selected:
			self.tabs = ["Workspace"]

	def compose(self) -> ComposeResult:
		with Vertical():
			yield Tabs(*self.tabs, id="confirmDelete-tabs")
			with Vertical(id="deletePage-container"):
				yield Label(f"This page will be deleted.")
				with Horizontal():
					yield Button(id="deletePage-confirm", label="Delete", variant="error")
					yield Button(id="deletePage-cancel", label="Cancel", variant="primary")
			with Vertical(id="deleteWorkspace-container"):
				yield Label(f"The workspace ({self.parent_screen.current_workspace}) and all of its contents will be deleted.")
				with Horizontal():
					yield Button(id="deleteWorkspace-confirm", label="Delete", variant="error")
					yield Button(id="deleteWorkspace-cancel", label="Cancel", variant="primary")

	def on_mount(self) -> None:
		if self.page_selected:
			workspace_container = self.query_one("#deleteWorkspace-container", Vertical)
			workspace_container.styles.display = "none"
		elif self.wksp_selected:
			workspace_container = self.query_one("#deletePage-container", Vertical)
			workspace_container.styles.display = "none"
	
	def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
		page_container = self.query_one("#deletePage-container", Vertical)
		workspace_container = self.query_one("#deleteWorkspace-container", Vertical)
		if event.tab.label == "Page":
			page_container.styles.display = "block"
			workspace_container.styles.display = "none"
		elif event.tab.label == "Workspace":
			page_container.styles.display = "none"
			workspace_container.styles.display = "block"
	
	def on_button_pressed(self, event: Button.Pressed) -> None:
		if event.button.id == "deleteWorkspace-confirm":
			self.parent_screen.run_worker(self.parent_screen.remove_workspace())
			self.app.pop_screen()
		elif event.button.id == "deleteWorkspace-cancel":
			self.app.pop_screen()
		elif event.button.id == "deletePage-confirm":
			self.parent_screen.run_worker(self.parent_screen.remove_page())
			self.app.pop_screen()
		elif event.button.id == "deletePage-cancel":
			self.app.pop_screen()

class PageWrapper:
	def __init__(self, content, history):
		self.content: str = content
		self.history = history

class EditorScreen(Screen):
	BINDINGS = [
		("ctrl+n", "new", "New..."),
		("ctrl+d", "delete", "Delete..."),
		("ctrl+s", "save", "Save"),
		("ctrl+e", "toggle_editor_view", "Toggle Editor"),
		("ctrl+t", "toggle_table_of_contents", "Toggle Table of Contents")
	]

	current_workspace: str = None
	current_page: int = None
	editor_hidden: bool = False

	editor_mode = "mixed"

	page_wrappers: dict[int, PageWrapper] = {}

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

	async def create_new_workspace(self, name: str) -> None:
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

	async def create_new_page(self, name: str) -> None:
		if type(self.current_workspace) == str:
			try:
				page_id = await self.app.db.create_page(name, self.current_workspace)
				pages = self.query_one("#editorScreen-pages", ListView)
				pages.append(ListItem(Label(name), name=f"page-{page_id}", id=f"page-{page_id}"))
			except Exception as e:
				self.notify(str(e), title="Database Error ⚠️", severity="warning", timeout=10)

	async def remove_page(self) -> None:
		if type(self.current_page) == int and self.current_page > 0:
			try:
				await self.app.db.delete_page(self.current_page)
				await self.update_pages()
			except Exception as e:
				self.notify(str(e), title="Database Error ⚠️", severity="warning", timeout=10)

	def action_toggle_editor_view(self) -> None:
		if not self.editor_hidden:
			text_area = self.query_one("#editorScreen-textArea")
			mdv = self.query_one("#editorScreen-preview")
			if self.editor_mode == "mixed":
				text_area.styles.display = "none"
				mdv.styles.width = "80%"
				self.editor_mode = "preview"
			elif self.editor_mode == "preview":
				mdv.styles.display = "none"
				text_area.styles.display = "block"
				text_area.styles.width = "80%"
				self.editor_mode = "editor"
			elif self.editor_mode == "editor":
				text_area.styles.display = "block"
				mdv.styles.display = "block"
				mdv.styles.width = "40%"
				text_area.styles.width = "40%"
				self.editor_mode = "mixed"
				
	def action_toggle_table_of_contents(self) -> None:
		if not self.editor_hidden:
			mdv = self.query_one("#editorScreen-preview", MarkdownViewer)
			mdv.show_table_of_contents = not mdv.show_table_of_contents
	
	def action_new(self) -> None:
		self.app.push_screen(CreateNewScreen(self))
	
	def action_delete(self) -> None:
		self.app.push_screen(ConfirmDelete(self))
	
	def action_save(self) -> None:
		self.run_worker(self.save(), exclusive=True)

	async def save(self) -> None:
		text_area = self.query_one("#editorScreen-textArea", TextArea)
		try:
			await self.app.db.update_page_content(self.current_page, text_area.text)
			self.notify(f"File saved to database successfully! ({self.current_page})", title="File Saved 💾")
		except Exception as e:
			self.notify(str(e), title="Database Error ⚠️", severity="warning", timeout=10)

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
	
	def set_current_page(self, page_id: int) -> None:
		self.unset_current_page()
		self.current_page = page_id
		if wrapper := self.page_wrappers.get(self.current_page):
			text_area = self.query_one("#editorScreen-textArea", TextArea)
			text_area.text = wrapper.content
			text_area.history = wrapper.history
		else:
			self.run_worker(self.update_page(), exclusive=True)

		page_list = self.query_one("#editorScreen-pages", ListView)
		page_list_item = page_list.query_one(f"#page-{page_id}", ListItem)
		page_list_item.focus()
		if self.editor_hidden:
			self.show_editor()

	def unset_current_page(self) -> None:
		self.hide_editor()
		text_area = self.query_one("#editorScreen-textArea", TextArea)
		self.page_wrappers[self.current_page] = PageWrapper(text_area.text, text_area.history)
		text_area.load_text("")
		mdv = self.query_one("#editorScreen-preview", MarkdownViewer)
		md = mdv.query_one(Markdown)
		md.update("")
		mdv.table_of_contents.refresh()
		self.current_page = None

	async def update_pages(self) -> None:
		pages = await self.app.db.get_pages(self.current_workspace)
		page_list = self.query_one("#editorScreen-pages", ListView)
		await page_list.clear()
		if len(pages) != 0:
			for page in pages:
				page_list.append(ListItem(Label(page["page_name"]), name=f"page-{page['page_id']}", id=f"page-{page['page_id']}"))
			self.set_current_page(pages[0]["page_id"])
		else:
			self.unset_current_page()

	async def update_page(self) -> None:
		page_content = await self.app.db.get_page_content(self.current_page)
		text_area = self.query_one("#editorScreen-textArea", TextArea)
		text_area.load_text(page_content)
		mdv = self.query_one("#editorScreen-preview", MarkdownViewer)
		md = mdv.query_one(Markdown)
		md.update(page_content)

	def on_mount(self) -> None:
		self.hide_editor()
		self.run_worker(self.update_workspaces(), exclusive=True)

	def on_list_view_selected(self, event: ListView.Selected) -> None:
		if event.list_view.id == "editorScreen-pages":
			self.set_current_page(int(event.item.name.replace("page-", "")))
	
	def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
		self.current_workspace = event.tab.label_text
		self.run_worker(self.update_pages(), exclusive=True)
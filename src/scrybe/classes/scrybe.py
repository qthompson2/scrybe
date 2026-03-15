from textual.app import App
from .login import LoginScreen
from .editor import EditorScreen

class Scrybe(App):
	SCREENS = {
		"login" : LoginScreen,
		"editor" : EditorScreen
	}
	CSS_PATH = "../styles/scrybe.tcss"
	_database = None

	def on_mount(self):
		self.theme = "gruvbox"
		self.title = "Scrybe"
		self.sub_title = "Markdown Editor"
		self.push_screen("login")
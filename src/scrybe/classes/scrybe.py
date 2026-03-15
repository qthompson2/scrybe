from textual.app import App
from .login import LoginScreen
from .editor import EditorScreen
from importlib.resources import files

class Scrybe(App):
	SCREENS = {
		"login" : LoginScreen,
		"editor" : EditorScreen
	}
	CSS_PATH = str(files("scrybe").joinpath("styles/scrybe.tcss"))
	db = None

	def on_mount(self):
		self.theme = "gruvbox"
		self.title = "Scrybe"
		self.sub_title = "Markdown Editor"
		self.push_screen("login")
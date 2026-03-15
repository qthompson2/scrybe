from textual.app import App
from classes import LoginScreen, EditorScreen

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
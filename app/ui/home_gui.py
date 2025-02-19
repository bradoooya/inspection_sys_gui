from PySide6.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout

class HomePage(QWidget):
    def __init__(self, root):
        self.root = root
        self.root.title("Home")
        self.root.geometry("400x400")
        self.root.resizable(False, False)

        self.frame = Frame(self.root)
        self.frame.pack()

        self.label = Label(self.frame, text="Home Page")
        self.label.pack()

        self.button = Button(self.frame, text="Go to About", command=self.go_to_about)
        self.button.pack()

    def go_to_about(self):
        self.root.destroy()
        about = Toplevel()
        AboutGui(about)
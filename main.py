import subprocess
from datetime import datetime
import win32api, win32con, win32gui
import win32com.client
import time
import psutil
import configparser

class RiotAutoLogin:
    def __init__(self, user, pwd):
        self.username = user
        self.password = pwd
        self.config = self._load_config()
        self.RIOTCLIENT_PATH = self.config['SETTINGS']['RIOTCLIENT_PATH']
    
    def _load_config(self):
        config = configparser.ConfigParser()
        config.read("config.ini")
        return config
    
    def _wait_for_window(self, window_title):
        while True:
            hwnd = win32gui.FindWindow(None, window_title)
            if hwnd:
                print(f'[{datetime.now().strftime("%H:%M:%S")}] {window_title} found')
                # Bring the window to the front
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                return hwnd
            time.sleep(1)  # Sleep for a short time before checking again

    def _send_login_keys(self):
        print(f'[{datetime.now().strftime("%H:%M:%S")}] Game launched')
        subprocess.Popen(self.RIOTCLIENT_PATH)
        print(f'[{datetime.now().strftime("%H:%M:%S")}] Riot Client started')#

        self._wait_for_window("Riot Client Main")
        
        shell = win32com.client.Dispatch("WScript.Shell")
        win32api.Sleep(3000)
        shell.SendKeys(self.username)
        shell.SendKeys("{TAB}")
        shell.SendKeys(self.password)
        shell.SendKeys("{ENTER}")

def is_process_running(process_name):
    """Check if there's any running process that matches the given name."""
    for proc in psutil.process_iter():
        try:
            pinfo = proc.as_dict(attrs=['pid', 'name', 'create_time'])
            if process_name.lower() in pinfo['name'].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            return False
    return False

## UI ## 
import sys, os
from datetime import datetime
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QEventLoop, QTimer
from PyQt6.QtGui import QIcon, QPalette, QColor, QPixmap, QBrush
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QHBoxLayout, QLabel, QSpacerItem, QSizePolicy, QDialog, QLineEdit, QPushButton
from qfluentwidgets import (setTheme, Theme, CardWidget, BodyLabel, SplashScreen, LineEdit, PushButton, ToolButton, FluentIcon, IconWidget)
from qframelesswindow import FramelessWindow

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def parse_config_and_create_cards(file_path, parent_widget):
    """Parse the config file and create credential cards."""
    config = configparser.ConfigParser()
    config.read(file_path)
    cards = []

    for section in config.sections():
        # Ensure the section has the expected keys
        if 'riot_username' in config[section]:
            riot_username = config[section]['riot_username']
            card = CredentialCard(FluentIcon.PEOPLE, riot_username, section, parent_widget)
            card.removed.connect(parent_widget.remove_from_config)  # Connect the signal
            cards.append(card)
        else: pass
    return cards

class CredentialCard(CardWidget):
    """Widget for displaying credentials."""
    # Signal emitted when the remove button is clicked
    removed = pyqtSignal(str)
    def __init__(self, icon, username, password, section, parent=None):
        super().__init__(parent)
        self.section = section  # Store the section name
        self.username = username
        self.password = password
        self.setup_ui(icon, username)

    def setup_ui(self, icon, title):
        """Initializes the UI components."""
        self.iconWidget = IconWidget(icon)
        self.titleLabel = BodyLabel(title, self)
        self.launchButton = PushButton('Launch', self)
        self.removeButton = ToolButton(FluentIcon.DELETE, self)

        # Layouts
        hBoxLayout = QHBoxLayout(self)
        vBoxLayout = QVBoxLayout()

        # Styling and Alignment
        self.setFixedHeight(83)
        hBoxLayout.setContentsMargins(20, 11, 20, 11)
        hBoxLayout.setSpacing(15)
        hBoxLayout.addWidget(self.iconWidget)
        vBoxLayout.addWidget(self.titleLabel, 0, Qt.AlignmentFlag.AlignVCenter)
        hBoxLayout.addLayout(vBoxLayout)
        hBoxLayout.addStretch(1)
        hBoxLayout.addWidget(self.launchButton, 0, Qt.AlignmentFlag.AlignRight)
        hBoxLayout.addWidget(self.removeButton, 0, Qt.AlignmentFlag.AlignRight)

        self.launchButton.clicked.connect(self.switch_account)
        self.removeButton.clicked.connect(self.remove_card)

    def switch_account(self):
        """Launch Riot Client with new creds and automate the login."""
        # Check if the Riot Client is already running
        login = RiotAutoLogin(self.username, self.password)
        if is_process_running('RiotClientServices.exe'):
            login._send_login_keys()
        else:
            print(f'[{datetime.now().strftime("%H:%M:%S")}] Riot Client failed to start.')
        
    def remove_card(self):
        """Emits the removed signal and hides the card."""
        self.removed.emit(self.section)  # Emit the section name
        self.hide()

class AddAccountDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Add Account")

        layout = QVBoxLayout(self)
        hBoxLayout = QHBoxLayout()  # No parent needed here

        self.username_input = LineEdit(self)
        self.username_input.setPlaceholderText("Username")
        layout.addWidget(self.username_input)

        self.password_input = LineEdit(self)
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)

        add_button = PushButton("Add", self)
        add_button.clicked.connect(self.accept)
        hBoxLayout.addWidget(add_button)

        cancel_button = PushButton("Cancel", self)
        cancel_button.clicked.connect(self.reject)
        hBoxLayout.addWidget(cancel_button)

        layout.addLayout(hBoxLayout)  # Add the horizontal box layout to the main vertical layout


        
class App(FramelessWindow):
    """Main Application Window."""
    def __init__(self):
        super().__init__()
        setTheme(Theme.DARK)
        self.setWindowIcon(QIcon('assets/iconVS.png'))
        self.cards = []
        self.thread = None

        self.splashScreen = SplashScreen(self.windowIcon(), self)
        self.splashScreen.setIconSize(QSize(102, 102))
        self.show()

        self.createSubInterface()
        self.splashScreen.finish()
        self.showMainSubInterface()

    def createSubInterface(self):
        loop = QEventLoop(self)
        QTimer.singleShot(1000, loop.quit)
        loop.exec()

    def showMainSubInterface(self):
        self.setup_ui()  # Set layout and properties
        self.setup_ui_components()  # Add components/widgets
        
    def add_fixed_spacer(self, layout, size):
        """Add a fixed spacer to the given layout."""
        spacer = QSpacerItem(size, size, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addSpacerItem(spacer)

    def setup_ui(self):
        """Initializes the main UI layout and properties."""
        setTheme(Theme.DARK)
        self.resize(400, 600)
        self.setWindowTitle('ValoSwitcher')
        self.setWindowIcon(QIcon(resource_path('assets/titleVS.png')))
        self.layout = QVBoxLayout(self)

    def setup_ui_components(self):
        """Initializes and adds the UI components/widgets."""
        self.layout.addSpacing(20)
        self.layout.addWidget(self.create_image_label())
        self.add_fixed_spacer(self.layout, 20)  # Add spacer
        cards = parse_config_and_create_cards("config.ini", self)
        for card in cards:
            self.layout.addWidget(card)
        self.spacer = self.layout.addStretch(1)  # Update this line
        self.layout.addWidget(self.create_add_button())
        self.layout.addSpacing(20)
        
    def add_account(self):
        dialog = AddAccountDialog()
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            username = dialog.username_input.text()
            password = dialog.password_input.text()

            # Save to config.ini
            self.save_to_config(username, password)

            # Refresh the app to show the new card
            self.refresh_ui()

    def save_to_config(self, username, password):
        config = configparser.ConfigParser()
        config.read("config.ini")

        # Assuming you want to increment the ACCOUNT number
        next_account_number = len(config.sections()) + 1
        section_name = f"ACCOUNT{next_account_number}"

        config[section_name] = {
            'riot_username': username,
            'password': password
        }

        with open("config.ini", "w") as config_file:
            config.write(config_file)

    def refresh_ui(self):
        """Refreshes the main UI."""
        # Clear widgets from the existing layout
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()
        self.setup_ui_components()

    def create_image_label(self):
        """Creates and returns an image label."""
        pixmap = QIcon("assets/titleVS.png").pixmap(200, 200)
        image_label = QLabel()
        image_label.setPixmap(pixmap)
        image_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        return image_label
    
    def create_credential_card(self, icon, username, password, content):
        """Creates and returns a credential card."""
        return CredentialCard(icon, username, password, content, self)

    def create_add_button(self):
        """Creates and returns a generate account button."""
        self.add_account_btn = PushButton('Add Account', self, FluentIcon.ADD)
        self.add_account_btn.clicked.connect(self.add_account)
        return self.add_account_btn
    
    def remove_from_config(self, section):
        """Remove an account from the config.ini file."""
        config = configparser.ConfigParser()
        config.read("config.ini")

        # Check if the section exists and remove it
        if config.has_section(section):
            config.remove_section(section)
            with open("config.ini", "w") as config_file:
                config.write(config_file)

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Styling
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    pixmap = QPixmap("assets/bg.png")
    brush = QBrush(pixmap)
    palette.setBrush(QPalette.ColorRole.Window, brush)
    app.setPalette(palette)

    window = App()
    window.show()
    app.exec()

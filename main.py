import subprocess
from datetime import datetime
import win32con, win32gui
import win32com.client
import time
import psutil
import pyautogui
import configparser
import os, sys

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for Nuitka """
    try:
        if getattr(sys, 'frozen', False):
            # Nuitka sets the `sys.frozen` attribute when the application is frozen
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class RiotAutoLogin:
    template_path = resource_path("assets/input.png")
    def __init__(self, user, pwd):
        self.username = user
        self.password = pwd
        self.config = self._load_config()
        self.RIOTCLIENT_PATH = self.config['SETTINGS']['RIOTCLIENT_PATH']
    
    def _load_config(self):
        config = configparser.ConfigParser()
        config.read(resource_path("config.ini"))
        return config
    
    def _wait_for_window(self, window_title):
        while True:
            hwnd = win32gui.FindWindow(None, window_title)
            if hwnd:
                print(f'[{datetime.now().strftime("%H:%M:%S")}] {window_title} found')
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                return hwnd
            time.sleep(1)

    def _check_for_input(self):
        location = pyautogui.locateOnScreen(self.template_path, confidence=0.8)
        if location is not None: return True
        return False

    def _send_login_keys(self):
        print(f'[{datetime.now().strftime("%H:%M:%S")}] Launching Riot Client')
        try:
            process = subprocess.Popen(self.RIOTCLIENT_PATH, stdout=subprocess.PIPE, stderr=subprocess.PIPE,text=True)  # Ensures the output is returned as a string)
            stdout, stderr = process.communicate()
            if stdout:
                print(f'[{datetime.now().strftime("%H:%M:%S")}] Riot Client started')
            if stderr:
                print("Error:\n", stderr)
        except FileNotFoundError as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] FAILED (FileNotFoundError): This is due to an incorrect Riot Client path in your config. Check it and try again.")
            exit(1)
            
        self._wait_for_window("Riot Client")
        shell = win32com.client.Dispatch("WScript.Shell")

        while True:
            if self._check_for_input():
                shell.SendKeys(self.username)
                shell.SendKeys("{TAB}")
                shell.SendKeys(self.password)
                shell.SendKeys("{ENTER}")
                break
        print(f'[{datetime.now().strftime("%H:%M:%S")}] SUCCESS: Logged in')
        exit(0)

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
import requests, urllib
import concurrent.futures
from datetime import datetime
from io import BytesIO
from dataclasses import dataclass
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QEventLoop, QTimer, QThread, pyqtSlot
from PyQt6.QtGui import QIcon, QPalette, QColor, QPixmap, QBrush, QPainter
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QHBoxLayout, QLabel, QSpacerItem, QSizePolicy, QDialog, QLineEdit, QPushButton, QWidget
from qfluentwidgets import (setTheme, Theme, CardWidget, BodyLabel, SplashScreen, LineEdit, PushButton, ToolButton, FluentIcon, StrongBodyLabel, BodyLabel, PopupTeachingTip, TeachingTipTailPosition, FlyoutViewBase, ImageLabel)
from qframelesswindow import FramelessWindow

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.collections
import numpy as np
from scipy.interpolate import CubicSpline
from matplotlib.colors import LinearSegmentedColormap, Normalize
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont

def create_level_tag(image_url, level):
    tmp_image = BytesIO(requests.get(image_url).content)
    tmp_image.seek(0)
    img = PIL.Image.open(tmp_image)
    draw = PIL.ImageDraw.Draw(img)
    font = PIL.ImageFont.load_default()

    # Get text size
    left, top, right, bottom = font.getbbox(level)
    text_width = right - left
    text_height = bottom - top
    
    image_width, image_height = img.size
    position = ((image_width - text_width) // 2, (image_height - text_height) // 2)
    
    # Draw text
    draw.text(position, level, (255, 255, 255), font=font)
    
    # Image to BytesIO
    output = BytesIO()
    img.save(output, format='PNG')
    output.seek(0)
    
    # BytesIO to QPixmap
    qpixmap = QPixmap()
    qpixmap.loadFromData(output.getvalue())
    return qpixmap

@dataclass
class AccountStats:
    banner : str = "https://titles.trackercdn.com/valorant-api/playercards/d1c85a2e-450d-f7e0-6ee3-469295cf1951/displayicon.png"
    account_level: int = 0
    account_level_tag_image:str = "https://media.valorant-api.com/levelborders/ebc736cd-4b6a-137b-e2b0-1486e31312c9/levelnumberappearance.png"
    shard: str = "eu"
    current_rank: str = "Unranked"
    current_rank_image: str = "https://trackercdn.com/cdn/tracker.gg/valorant/icons/tiersv2/0.png"
    peak_rank: str = "Unranked"
    peak_rank_image: str = "https://trackercdn.com/cdn/tracker.gg/valorant/icons/tiersv2/0.png"
    current_season_time_played : str = "0"
    kda_ratios: list = None

class MatchesGraph(QWidget):
    def __init__(self, data):
        super().__init__()
        self.kd_ratios = data
        self.setGeometry(30, 30, 30, 30)

        layout = QVBoxLayout(self)

        self.figure = Figure(figsize=(10, 6), dpi=100)
        self.figure.patch.set_alpha(0)

        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background:transparent;")
        layout.addWidget(self.canvas)

        self.plot_chart()

    def plot_chart(self):
        # Original data points
        y = np.array(self.kd_ratios)
        x = np.array(range(len(self.kd_ratios)))

        # Cubic Spline Interpolation
        cs = CubicSpline(x, y)

        # Generate smooth points
        x_smooth = np.linspace(x.min(), x.max(), 2000)
        y_smooth = cs(x_smooth)

        ax = self.figure.add_subplot(111)
        ax.patch.set_alpha(0)

        # Create custom colormap for gradient
        colors = ["#0d0b37", "#0d0b37"] # "#05a2b2", #862F3B
        n_bins = 256
        cmap = LinearSegmentedColormap.from_list('custom', colors, N=n_bins)

        # Plot the line with gradient color
        points = np.array([x_smooth, y_smooth]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)
        
        norm = Normalize(0.25, 1.75)
        
        lc = matplotlib.collections.LineCollection(segments, cmap=cmap, norm=norm)
        lc.set_array(y_smooth)
        lc.set_linewidth(1)
        line = ax.add_collection(lc)

        ax.fill_between(x_smooth, y_smooth, color="#0d0b37", alpha=0.3)
        ax.set_xlim(x.min(), x.max())
        ax.set_ylim(min(y.min() * 0.9, 0), max(y.max() * 1.1, 1.1))

        # Remove x and y axis labels
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.set_xticks([])
        ax.set_yticks([])
        ax.grid(False)

        # Remove the frame
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)
        
        # Add grid
        ax.grid(False, linestyle=':', alpha=0.2)

        # Improve layout
        self.figure.tight_layout()
        self.canvas.draw()

class Image(QLabel):
    def __init__(self, image_url, parent=None):
        super().__init__(parent)
        self.setPixmap(self.load_pixmap_from_url(image_url))

    def load_pixmap_from_url(self, url):
        response = requests.get(url)
        if response.status_code == 200:
            image = QPixmap()
            image.loadFromData(BytesIO(response.content).read())
            return image
        else:
            return QPixmap()

    def scaledToHeight(self, height):
        self.setPixmap(self.pixmap().scaledToHeight(height, Qt.TransformationMode.SmoothTransformation))

    def setBorderRadius(self, radius):
        pass


class CredentialLoader(QThread):
    credentials_loaded = pyqtSignal(list)

    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path

    def run(self):
        config = configparser.ConfigParser()
        config.read(self.file_path)
        credentials = []

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_credential = {
                executor.submit(self.fetch_account, section, config[section]): (section, config[section])
                for section in config.sections() if 'riot_username' in config[section]
            }
            for future in concurrent.futures.as_completed(future_to_credential):
                section, data = future_to_credential[future]
                try:
                    rank_data = future.result()
                    riot_username = data['riot_username']
                    pwd = data['password']
                    in_game_name, in_game_tag = data['name'].split(":")
                    credentials.append((riot_username, pwd, (in_game_name, in_game_tag), section, rank_data))
                except Exception as e:
                    print(f'[{datetime.now().strftime("%H:%M:%S")}] Failed to retrieve rank data for {section}: {e}')

        self.credentials_loaded.emit(credentials)

    def fetch_account(self, section, data):
        in_game_name, in_game_tag = data['name'].split(":")
        headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.5',
                'Origin': 'https://tracker.gg',
                'Referer': 'https://tracker.gg/',
            }
        endpoint = requests.get(
            f"https://api.tracker.gg/api/v2/valorant/standard/profile/riot/{urllib.parse.unquote(in_game_name)}%23{urllib.parse.quote(in_game_tag)}?source=web",
            headers=headers
        )
        endpoint.raise_for_status()
        data = endpoint.json()
        segments = data['data']['segments']
        if segments[0]['attributes']["playlist"] != "competitive":
            segment = next(filter(lambda s: s.get('attributes', {}).get('playlist') == "competitive", segments), False)
            if not segment:
                print("No competitive data found, fetching in different endpoint")
                params = {
                    'playlist': 'competitive',
                    'source': 'web',
                }
                comp_segments = requests.get(
                    f'https://api.tracker.gg/api/v2/valorant/standard/profile/riot/{urllib.parse.unquote(in_game_name)}%23{urllib.parse.quote(in_game_tag)}/segments/playlist',
                    params=params,
                    headers=headers,
                )
                print(comp_segments.status_code)
                segment = comp_segments.json()['data'][0]
        else:
            segment = segments[0]

        kda_ratios = self.fetch_rank_matches_kda_ratios(in_game_name, in_game_tag)

        return AccountStats(
            banner=data['data']['platformInfo']['avatarUrl'],
            account_level=data['data']['metadata']['accountLevel'], 
            account_level_tag_image=self.get_level_number_appearance(data['data']['metadata']['accountLevel']),
            shard=data['data']['metadata']['activeShard'],
            current_season_time_played=segments[0]['stats']['timePlayed']['displayValue'],
            current_rank=segment['stats']['rank']['metadata']['tierName'], 
            current_rank_image=segment['stats']['rank']['metadata']['iconUrl'], 
            peak_rank=segment['stats']['peakRank']['metadata']['tierName'], 
            peak_rank_image=segment['stats']['peakRank']['metadata']['iconUrl'], 
            kda_ratios=kda_ratios
        )

    def fetch_rank_matches_kda_ratios(self, name, tag):
        in_game_name, in_game_tag = name, tag
        headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'en-US,en;q=0.5',
                'Origin': 'https://tracker.gg',
                'Referer': 'https://tracker.gg/',
            }
        endpoint = requests.get(
            f"https://api.tracker.gg/api/v2/valorant/standard/matches/riot/{urllib.parse.unquote(in_game_name)}%23{urllib.parse.quote(in_game_tag)}?type=competitive&season=&agent=all&map=all",
            headers=headers
        )
        endpoint.raise_for_status()
        data = endpoint.json()
        kd_ratios = []
        for match in data['data']['matches']:
            for segment in match['segments']:
                if 'kdRatio' in segment['stats']:
                    kd_ratios.append(segment['stats']['kdRatio']['value'])
        return kd_ratios
    
    def get_level_number_appearance(self, account_level):
        closest_index = None
        closest_url = None
        level_borders_id = ('ebc736cd-4b6a-137b-e2b0-1486e31312c9', '5156a90d-4d65-58d0-f6a8-48a0c003878a', '9c4afb15-40d7-3557-062a-4bb198cb9958', 'e6238102-425c-a647-6685-e6af7f8982d9', '49413ac2-4ed5-6953-5791-db838ccb58f3', 'e05371e3-4ec4-a53e-168a-c49346a75c19', '7e7feff1-44c2-301e-767d-d9b2b1cd9051', '53d4ed03-4b29-5913-aeda-80a41afcef3a', '6f610ab6-4a21-63fd-ac19-4a9204bc2721', '547ac9dd-495d-f11d-d921-3fbd14604ae0', 'bd1082ab-462c-3fb8-e049-28a9750acf0f', '37a36996-41f3-6e26-c00b-46bf7c037482', '5d0d6c6c-4f0a-dc65-e506-b786cc27dbe1', '3635b061-4bf9-b937-55fe-44a4dd0ed3dc', 'ae5eda0d-476b-a159-959c-df93374f4a69', '3d90bc3a-4626-71d6-a17c-93ae14d05fb0', '674bbd9e-4a4f-208a-75fa-1d9dd7d7008f', 'd84cf377-4c21-1cdf-0260-4e8ebd9825f5', '6c1fb61e-46e5-2908-5048-d4866cb64c3d', 'af1852a5-4e66-02a6-2ae3-ab8c885efb80', 'cbd1914e-43f8-7ae5-38c4-228bcbe58756', 'c8a4abff-4ace-f0a3-c9f3-db936791a697', '086dd1ab-4889-793a-4b33-0a99e311fa25', '08ab72f1-4fce-ddb5-5fd5-22abd3bc9d49', '6694d7f7-4ab9-8545-5921-35a9ea8cec24') 

        try:
            for i in range(len(level_borders_id)):
                starting_level = i * 20 + 1
                if starting_level <= account_level:
                    closest_index = i
                else:
                    break
        except Exception:
            closest_index = 0
        if closest_index is not None and closest_index < len(level_borders_id):
            closest_border_id = level_borders_id[closest_index]
            closest_url = f"https://media.valorant-api.com/levelborders/{closest_border_id}/levelnumberappearance.png"

        return closest_url

class AccountDetailsView(FlyoutViewBase):
    def __init__(self, rank_data=None, parent=None):
        super().__init__(parent)
        self.rank_data = rank_data
        self.hBoxLayout = QHBoxLayout(self)
        self.hBoxLayout.setSpacing(10)
        self.infoLayout = QVBoxLayout()

        topInfoLayout = QHBoxLayout()
        self.accoutLevelLayout = QVBoxLayout()
        self.accoutLevelLayout.setSpacing(0)
        altitle = BodyLabel("Level")
        altitle.setStyleSheet("font-size: 12px;")
        self.accoutLevelLayout.addWidget(altitle, 0, Qt.AlignmentFlag.AlignHCenter)
        self.accoutLevelLayout.addWidget(StrongBodyLabel(str(self.rank_data.account_level)), 0, Qt.AlignmentFlag.AlignHCenter) 
        self.timePlayedLayout = QVBoxLayout()
        self.timePlayedLayout.setSpacing(0)
        tptitle = BodyLabel("Time Played")
        tptitle.setStyleSheet("font-size: 12px;")
        self.timePlayedLayout.addWidget(tptitle, 0, Qt.AlignmentFlag.AlignHCenter)
        self.timePlayedLayout.addWidget(StrongBodyLabel(self.rank_data.current_season_time_played),0, Qt.AlignmentFlag.AlignHCenter)
        topInfoLayout.addLayout(self.accoutLevelLayout)
        topInfoLayout.addLayout(self.timePlayedLayout)

        bottomInfoLayout = QHBoxLayout()
        currentRankLayout = QVBoxLayout()
        currentRankLayout.setSpacing(0)
        crtitle = BodyLabel("Current Rank")
        crtitle.setStyleSheet("font-size: 12px;")
        rank_image = Image(self.rank_data.current_rank_image)
        rank_image.scaledToHeight(15)
        rankTitleLayout = QHBoxLayout()
        rankTitleLayout.setSpacing(2)
        rankTitleLayout.addWidget(crtitle, 0, Qt.AlignmentFlag.AlignHCenter)
        rankTitleLayout.addWidget(rank_image)
        currentRankLayout.addLayout(rankTitleLayout)
        currentRankLayout.addWidget(StrongBodyLabel(self.rank_data.current_rank), 0, Qt.AlignmentFlag.AlignHCenter)

        peakRankLayout = QVBoxLayout()
        peakRankLayout.setSpacing(0)
        prtitle = BodyLabel("Peak Rank")
        prtitle.setStyleSheet("font-size: 12px;")
        peak_image = Image(self.rank_data.peak_rank_image)
        peak_image.scaledToHeight(15)
        peakTitleLayout = QHBoxLayout()
        peakTitleLayout.setSpacing(2)
        peakTitleLayout.addWidget(prtitle, 0, Qt.AlignmentFlag.AlignHCenter)
        peakTitleLayout.addWidget(peak_image)
        peakRankLayout.addLayout(peakTitleLayout)
        peakRankLayout.addWidget(StrongBodyLabel(self.rank_data.peak_rank), 0, Qt.AlignmentFlag.AlignHCenter)

        bottomInfoLayout.addLayout(currentRankLayout)
        bottomInfoLayout.addLayout(peakRankLayout)

        self.infoLayout.addLayout(topInfoLayout)
        self.infoLayout.addLayout(bottomInfoLayout)
        self.hBoxLayout.addLayout(self.infoLayout)

        bannerLayout = QHBoxLayout()
        banner_image = self.load_pixmap_from_url(self.rank_data.banner)
        level_tag = create_level_tag(self.rank_data.account_level_tag_image, str(self.rank_data.account_level))  # Adjust height as needed

        combined_pixmap = QPixmap(banner_image.size())
        combined_pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(combined_pixmap)

        painter.drawPixmap(0, 0, banner_image)
        x = (banner_image.width() - level_tag.width()) // 2
        y = banner_image.height() - level_tag.height() - 2
        painter.drawPixmap(x, y, level_tag)
        painter.end()

        banner_label = ImageLabel()
        banner_label.setPixmap(combined_pixmap)
        banner_label.setBorderRadius(8, 8, 8, 8)
        self.hBoxLayout.addWidget(banner_label)

        # Add KDA chart
        if self.rank_data.kda_ratios:
            kda_chart = MatchesGraph(self.rank_data.kda_ratios)
            kda_chart.setFixedHeight(50)
            kda_chart.setFixedWidth(200)
            self.infoLayout.addWidget(kda_chart)

    def load_pixmap_from_url(self, url):
        response = requests.get(url)
        if response.status_code == 200:
            image = QPixmap()
            image.loadFromData(BytesIO(response.content).read())
            return image
        else:
            # Handle failed download or return a default image
            return QPixmap()

    def paintEvent(self, e):
        pass


class CredentialCard(CardWidget):
    """Widget for displaying credentials."""
    # Signal emitted when the remove button is clicked
    removed = pyqtSignal(str)

    def __init__(self, username, password, in_game: tuple, section, rank_data, parent=None):
        super().__init__(parent)
        self.section = section  # Store the section name
        self.username = username
        self.password = password
        self.in_game = in_game
        self.rank_data = rank_data

        to_display = (self.username, "") if not self.in_game else self.in_game
        current_rank_image = Image(self.rank_data.current_rank_image)
        peak_rank_image = Image(self.rank_data.peak_rank_image)
        current_rank_image.scaledToHeight(40)
        peak_rank_image.scaledToHeight(15)
        self.setup_ui(current_rank_image, peak_rank_image, to_display)
        self.clicked.connect(self.setup_details_tooltip)

    def download_background_image(self, image_url):
        response = requests.get(image_url)
        if response.status_code == 200:
            image = QPixmap()
            image.loadFromData(BytesIO(response.content).read())
            return image

    def setup_details_tooltip(self):
        print("Showing details")
        PopupTeachingTip.make(
            target=self,
            view=AccountDetailsView(self.rank_data, self), # CustomFlyoutView(), # AccountDetailsView(self.rank_data, self),
            tailPosition=TeachingTipTailPosition.RIGHT,
            duration=2000,
            parent=self
        )

    def setup_ui(self, current_rank, peak_rank, title):
        """Initializes the UI components."""
        self.currentRank = current_rank
        self.peakRank = peak_rank
        # Create separate labels for in-game name and tag
        self.inGameNameLabel = QLabel(title[0], self)
        self.inGameNameLabel.setStyleSheet("font-weight: bold; font-size: 16px;")
        self.inGameTagLabel = QLabel(f"#{title[1]}", self)
        self.inGameTagLabel.setStyleSheet("color: gray;")
        
        self.launchButton = PushButton('Launch', self)
        self.removeButton = ToolButton(FluentIcon.DELETE, self)

        # Layouts
        self.hBoxLayout = QHBoxLayout(self)
        self.hBoxLayout.setContentsMargins(20, 11, 11, 11)
        self.hBoxLayout.setSpacing(15)
        nameTagLayout = QVBoxLayout()
        nameTagLayout.setContentsMargins(0, 0, 0, 0)
        nameTagLayout.setSpacing(0)
        rankLayout = QHBoxLayout()
        rankLayout.setSpacing(2)

        # Styling and Alignment
        self.setFixedHeight(83)
        
        rankLayout.addWidget(self.peakRank)
        rankLayout.addWidget(self.currentRank)
    
        nameTagLayout.addWidget(self.inGameNameLabel, 0, Qt.AlignmentFlag.AlignVCenter)
        nameTagLayout.addWidget(self.inGameTagLabel, 0, Qt.AlignmentFlag.AlignVCenter)
        nameTagLayout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.hBoxLayout.addLayout(rankLayout)
        self.hBoxLayout.addLayout(nameTagLayout)
        self.hBoxLayout.addStretch(1)
        self.hBoxLayout.addWidget(self.launchButton, 0, Qt.AlignmentFlag.AlignRight)
        self.hBoxLayout.addWidget(self.removeButton, 0, Qt.AlignmentFlag.AlignRight)

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
        ingameLayout = QHBoxLayout()

        self.in_game_name = LineEdit(self)
        self.in_game_name.setPlaceholderText("In-game Name")
        ingameLayout.addWidget(self.in_game_name)
        self.in_game_tag = LineEdit(self)
        self.in_game_tag.setPlaceholderText("In-game Tag")
        ingameLayout.addWidget(self.in_game_tag)

        layout.addLayout(ingameLayout)

        self.username_input = LineEdit(self)
        self.username_input.setPlaceholderText("Riot Username")
        layout.addWidget(self.username_input)

        self.password_input = LineEdit(self)
        self.password_input.setPlaceholderText("Riot Password")
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
    rank_data_fetched = pyqtSignal(tuple)
    def __init__(self):
        super().__init__()
        setTheme(Theme.DARK)
        self.setWindowIcon(QIcon(resource_path('assets/iconVS.png')))
        self.cards = []
        self.thread = None

        self.splashScreen = SplashScreen(self.windowIcon(), self)
        self.splashScreen.setIconSize(QSize(102, 102))
        self.splashScreen.show()

        self.credentialLoader = CredentialLoader(resource_path("config.ini"))
        self.credentialLoader.credentials_loaded.connect(self.on_credentials_loaded)
        self.credentialLoader.start()
        self.rank_data_fetched.connect(self.add_new_card)

    @pyqtSlot(list)
    def on_credentials_loaded(self, credentials):
        for credential in credentials:
            riot_username, pwd, in_game, section, rank_data = credential
            card = CredentialCard(riot_username, pwd, in_game, section, rank_data, self)
            card.removed.connect(self.remove_from_config)
            self.cards.append(card)

        self.createSubInterface()
        self.splashScreen.finish()
        self.showMainSubInterface()

    def createSubInterface(self):
        loop = QEventLoop(self)
        QTimer.singleShot(2000, loop.quit)
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
        for card in self.cards:
            self.layout.addWidget(card)
        self.spacer = self.layout.addStretch(1)  # Update this line
        self.layout.addWidget(self.create_add_button())
        self.layout.addSpacing(20)

    def add_account(self):
        dialog = AddAccountDialog()
        result = dialog.exec()

        if result == QDialog.DialogCode.Accepted:
            name = f'{dialog.in_game_name.text()}:{dialog.in_game_tag.text()}'
            username = dialog.username_input.text()
            password = dialog.password_input.text()

            # Save to config.ini
            self.save_to_config(name, username, password)
            self.fetch_rank_and_add_new_card(name, username, password)

    def save_to_config(self, name, username, password):
        config = configparser.ConfigParser()
        config.read(resource_path("config.ini"))

        next_account_number = len(config.sections()) + 1
        section_name = f"ACCOUNT{next_account_number}"

        config[section_name] = {
            'name': name,
            'riot_username': username,
            'password': password
        }

        with open(resource_path("config.ini"), "w") as config_file:
            config.write(config_file)

    def fetch_rank_and_add_new_card(self, name, username, password):
        in_game_name, in_game_tag = name.split(":")
        section_name = f"ACCOUNT{len(self.cards) + 1}"  # New section name

        def fetch_rank():
            try:
                rank_data = self.credentialLoader.fetch_account(section_name, {
                    'name': name,
                    'riot_username': username,
                    'password': password
                })
                self.rank_data_fetched.emit((username, password, (in_game_name, in_game_tag), section_name, rank_data))
            except Exception as e:
                print(f'[{datetime.now().strftime("%H:%M:%S")}] Failed to retrieve rank data for {section_name}: {e}')

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        executor.submit(fetch_rank)

    @pyqtSlot(tuple)
    def add_new_card(self, credential):
        username, password, in_game, section_name, rank_data = credential
        new_card = CredentialCard(username, password, in_game, section_name, rank_data, self)
        new_card.removed.connect(self.remove_from_config)
        self.cards.append(new_card)
        self.layout.insertWidget(self.layout.count() - 3, new_card)

    def create_image_label(self):
        """Creates and returns an image label."""
        pixmap = QIcon(resource_path("assets/titleVS.png")).pixmap(200, 200)
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
        # Also remove the card from the UI and the list of cards
        for card in self.cards:
            if card.section == section:
                self.layout.removeWidget(card)
                card.deleteLater()
                self.cards.remove(card)
                break

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
    pixmap = QPixmap(resource_path("assets/bg.png"))
    painter = QPainter(pixmap)
    overlay = QColor(0, 0, 0, 150)
    painter.fillRect(pixmap.rect(), overlay)
    painter.end()
    brush = QBrush(pixmap)
    palette.setBrush(QPalette.ColorRole.Window, brush)
    app.setPalette(palette)

    window = App()
    window.show()
    app.exec()

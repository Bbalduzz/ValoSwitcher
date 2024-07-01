<h1 align="center">
  <img src="https://github.com/Bbalduzz/ValoSwitcher/assets/81587335/7eb2daa1-44eb-44a2-b76e-f6d40b9e59d6" alt="valoswitch logo" width="300"/>
</h1>


<h4 align="center">A sharp looking tool to switch between your valorant accounts<br>Local. Free. Open Source.</h4>

<p align="center">
  <a href="#documentation">Documentation</a> •
  <a href="#support">Support Me</a>
</p>

<div align="center">
  <img src="https://github.com/Bbalduzz/ValoSwitcher/assets/81587335/dd586c13-647f-4e86-a7e0-46fc1244f54d" alt="valoswitch"/>
</div>

### How to use
- change the `RIOTCLIENT_PATH` in config.ini to your riotclient's path
- add your riot accounts in the config.ini:
   1. __manually__: follow this structure:
        ```ini
        [ACCOUNT1]
        name = in_game_username:tag
        riot_username = xxxxxxxxxx
        password = xxxxxx
        
        [ACCOUNT2]
        name = in_game_username:tag
        riot_username = xxxxxxxxxx
        password = xxxxxx
        ...
        ```
   2. or add them though ValoSwitch clicking "Add Account"
   
### How to compile
- `py -m PyInstaller --windowed --onefile main.py`
- copy the assets folder and the config.ini in the newly created `dist` folder

### Demo
https://github.com/Bbalduzz/ValoSwitcher/assets/81587335/066a6350-b045-45e4-bd9b-5d1ac75dd417


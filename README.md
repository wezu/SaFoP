# SaFoP
Standalone Fonline Planer

![screenshot](https://raw.githubusercontent.com/wezu/SaFoP/master/screenshot.png)

## How to run?
To run this program you will need to install Python and Kivy.

To install Python go to https://www.python.org/downloads/ download and install any 3.7.x version.

To install Kivy:
- Open a command prompt/console (on Windows: type `cmd` in 'Search' to open one)
- If you're on Windows: In the command prompt type in (copy/paste):
 `python -m pip install docutils pygments pypiwin32 kivy_deps.sdl2==0.1.* kivy_deps.glew==0.1.*`
- If you're on Linux you might need to install pip (`sudo apt install python3-pip`)
- In the command prompt/console type in (copy/paste): `python -m pip install kivy`

If You are using Python 3.8+: download and use one of the wheels from this list https://kivy.org/downloads/simple/kivy/ (or try: `python -m pip install kivy --pre --extra-index-url https://kivy.org/downloads/simple/`)

If You are using Python 2.7.x - why!?

To run the program type in `python main.py` after navigating to the directory where you downloaded the content of this repository.

## Binary for windows
You can get a pre-build binary for Windows here (You won't need Python nor Kivy to run it):

https://github.com/wezu/SaFoP/releases/download/3.1/safop_s3_1_win32.zip

It is made by just packing Python +Kivi + scripts and using sitecustomize.py to import the modules automagically. Antivirus software should not detect it anymore https://www.virustotal.com/gui/file/a4512897721f874a0de12981e637178093db78118ebbd49693b21d74eb4e2abc/detection

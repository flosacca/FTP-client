OPTIONS = -F -w --additional-hooks-dir . -i shell32_251.ico

all:
	pyinstaller $(OPTIONS) main.py

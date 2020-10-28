OPTIONS = -F -w --additional-hooks-dir=.

all:
	pyinstaller $(OPTIONS) main.py

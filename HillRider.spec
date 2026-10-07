# PyInstaller build recipe: `pyinstaller HillRider.spec`
# Produces dist/HillRider/ with a double-clickable HillRider executable.

a = Analysis(
    ["main.py"],
    datas=[("assets", "assets")],
    hiddenimports=[],
    excludes=["tkinter", "matplotlib", "scipy", "PIL"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="HillRider",
    console=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="HillRider")

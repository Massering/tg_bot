from cx_Freeze import setup, Executable

setup(
    name="FMS_bot",
    version="0.1",
    description="tg_bot",
    executables=[Executable("main.py")]
)

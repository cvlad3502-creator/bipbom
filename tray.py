import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(sys.executable))
while HERE and not os.path.exists(os.path.join(HERE, "bot.py")):
    parent = os.path.dirname(HERE)
    if parent == HERE:
        break
    HERE = parent
os.chdir(HERE)
sys.path.insert(0, HERE)

TOKEN_FILE = os.path.join(HERE, "token.txt")
LOG = os.path.join(HERE, "log.txt")


def read_token() -> str:
    if os.getenv("BOT_TOKEN"):
        return os.getenv("BOT_TOKEN").strip()
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, encoding="utf-8") as f:
            return f.read().strip()
    return ""


def fail(text: str) -> None:
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(text + "\n")
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, text, "BipBom", 0x10)
    except Exception:
        print(text)


def main() -> None:
    token = read_token()
    if not token:
        import tkinter as tk
        from tkinter import simpledialog

        root = tk.Tk()
        root.withdraw()
        token = simpledialog.askstring("BipBom", "Вставьте токен от @BotFather:", parent=root) or ""
        root.destroy()
        token = token.strip()
        if not token:
            return
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(token)
    os.environ["BOT_TOKEN"] = token
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    try:
        import bot

        bot.main()
    except SystemExit:
        pass
    except Exception:
        fail("Бот остановился с ошибкой:\n\n" + traceback.format_exc()[-1500:])


if __name__ == "__main__":
    main()

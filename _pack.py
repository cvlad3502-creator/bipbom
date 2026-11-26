import os
import zipfile

SRC = r"C:\Users\виктория\Documents\MultiTool\BipBom"
OUT = os.path.join(SRC, "render-upload.zip")
FILES = [
    "bot.py",
    "app.py",
    "web/index.html",
    "requirements.txt",
    "start.cmd",
    "Procfile",
    "runtime.txt",
    "render.yaml",
]
SKIP = {"bipbom.db", "token.txt", "log.txt", ".venv"}

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for rel in FILES:
        path = os.path.join(SRC, rel.replace("/", os.sep))
        if not os.path.isfile(path):
            raise SystemExit(f"нет файла: {rel}")
        z.write(path, rel)

for name in os.listdir(SRC):
    assert name not in SKIP or name not in zipfile.ZipFile(OUT).namelist()

with zipfile.ZipFile(OUT) as z:
    print("\n".join(f"{i.filename}  {i.file_size} байт" for i in z.infolist()))
    bad = [n for n in z.namelist() if n in SKIP or "token" in n.lower()]
    print("утечка секретов:", bad or "нет")
print("архив:", OUT, os.path.getsize(OUT), "байт")

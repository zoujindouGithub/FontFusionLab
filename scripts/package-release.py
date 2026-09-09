import hashlib
import os
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MERGED = os.path.join(ROOT, "merged-v4")
RELEASE_DIR = os.path.join(ROOT, "release")
ZIP_NAME = "FiraCodeMapleMono-v1.0.zip"
ZIP_PATH = os.path.join(RELEASE_DIR, ZIP_NAME)

os.makedirs(RELEASE_DIR, exist_ok=True)

files_to_pack = [
    (os.path.join(MERGED, "FiraCodeMapleMono-Regular.ttf"), "FiraCodeMapleMono-Regular.ttf"),
    (os.path.join(MERGED, "FiraCodeMapleMono-Bold.ttf"), "FiraCodeMapleMono-Bold.ttf"),
    (os.path.join(MERGED, "FiraCodeMapleMono-Italic.ttf"), "FiraCodeMapleMono-Italic.ttf"),
    (os.path.join(MERGED, "FiraCodeMapleMono-BoldItalic.ttf"), "FiraCodeMapleMono-BoldItalic.ttf"),
    (os.path.join(ROOT, "LICENSE"), "LICENSE"),
    (os.path.join(ROOT, "README.md"), "README.md"),
    (os.path.join(ROOT, "README.en.md"), "README.en.md"),
]

print("打包 Release zip...")
with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
    for src, arc in files_to_pack:
        if not os.path.exists(src):
            raise FileNotFoundError(f"Missing required file: {src}")
        zf.write(src, arc)
        size_mb = os.path.getsize(src) / (1024 * 1024)
        print(f"  + {arc} ({size_mb:.2f} MB)")

zip_size_mb = os.path.getsize(ZIP_PATH) / (1024 * 1024)
h = hashlib.sha256(open(ZIP_PATH, "rb").read()).hexdigest()

print(f"\n[OK] Release 包创建成功: {ZIP_PATH} ({zip_size_mb:.2f} MB)")
print(f"SHA-256: {h}")

with open(os.path.join(RELEASE_DIR, "SHA256SUMS.txt"), "w") as f:
    f.write(f"{h}  {ZIP_NAME}\n")

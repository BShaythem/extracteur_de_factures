import os
import glob

IMG_DIR = "data/invoices-donut/train"  # Change as needed
SUPPORTED_EXTS = [".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"]

# Get all image files
files = []
for ext in SUPPORTED_EXTS:
    files.extend(glob.glob(os.path.join(IMG_DIR, f"*{ext}")))

files.sort()  # Sort for reproducibility

for idx, file_path in enumerate(files, 1):
    ext = os.path.splitext(file_path)[1].lower()
    new_name = f"train-{idx}{ext}"
    new_path = os.path.join(IMG_DIR, new_name)
    os.rename(file_path, new_path)
    print(f"Renamed {file_path} -> {new_path}") 
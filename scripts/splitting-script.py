import os
import random
import shutil

# Set your source and target directories
SOURCE_DIR = "data/invoices-donut/images"  # Folder with all images
TARGET_ROOT = "data/invoices-donut"        # Root where split folders will be created

# Output split folders
SPLITS = {
    "train": 0.8,
    "valid": 0.1,
    "test": 0.1
}

# Get all image files
image_files = [f for f in os.listdir(SOURCE_DIR) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
random.shuffle(image_files)

n_total = len(image_files)
n_train = int(n_total * SPLITS["train"])
n_valid = int(n_total * SPLITS["valid"])
n_test = n_total - n_train - n_valid  # Ensure all files are used

splits = {
    "train": image_files[:n_train],
    "valid": image_files[n_train:n_train + n_valid],
    "test": image_files[n_train + n_valid:]
}

for split, files in splits.items():
    split_dir = os.path.join(TARGET_ROOT, split)
    os.makedirs(split_dir, exist_ok=True)
    for fname in files:
        shutil.copy2(os.path.join(SOURCE_DIR, fname), os.path.join(split_dir, fname))

print(f"Done! {n_train} train, {n_valid} valid, {n_test} test images.")
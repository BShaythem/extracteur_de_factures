import os
import glob
import math

IMG_DIR = "data/invoices/train"
BATCH_SIZE = 100
SUPPORTED_EXTS = [".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"]

# Get all image files (after renaming)
files = []
for ext in SUPPORTED_EXTS:
    files.extend(glob.glob(os.path.join(IMG_DIR, f"*{ext}")))

files.sort()  # Ensure order

num_batches = math.ceil(len(files) / BATCH_SIZE)

for batch_idx in range(num_batches):
    batch_files = files[batch_idx*BATCH_SIZE : (batch_idx+1)*BATCH_SIZE]
    # Do something with batch_files, e.g., save their names to a file
    with open(f"batch_{batch_idx+1}.txt", "w") as f:
        for file_path in batch_files:
            f.write(f"{file_path}\n")
    print(f"Batch {batch_idx+1}: {len(batch_files)} files")
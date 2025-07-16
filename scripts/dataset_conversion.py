import json
import os
import paddle
import sys
# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.utils.utils import preprocess_image_for_ocr, ocr_tokens_and_bboxes, bio_tag_tokens

splits = [
    ("train", "layoutlmv3_train.jsonl", "layoutlmv3_train_filtered.jsonl"),
    ("valid", "layoutlmv3_valid.jsonl", "layoutlmv3_valid_filtered.jsonl"),
    ("test", "layoutlmv3_test.jsonl", "layoutlmv3_test_filtered.jsonl")
]
print("PaddlePaddle is compiled with CUDA:", paddle.is_compiled_with_cuda())
print("PaddlePaddle is using GPU:", paddle.device.get_device())
for split_name, out_jsonl, out_filtered in splits:
    # Load COCO JSON for this split
    coco_path = f"data/invoices-8/{split_name}/_annotations.coco.json"
    if not os.path.exists(coco_path):
        print(f"No COCO file for split {split_name}, skipping.")
        continue

    with open(coco_path, "r") as f:
        coco = json.load(f)

    images = {img['id']: img for img in coco['images']}
    categories = {cat['id']: cat['name'] for cat in coco['categories']}
    annotations = coco['annotations']
    # Create a mapping of image IDs to their regions
    regions_per_image = {}
    for ann in annotations:
        img_id = ann['image_id']
        bbox = ann['bbox']
        label = categories[ann['category_id']]
        regions_per_image.setdefault(img_id, []).append({'bbox': bbox, 'label': label})

    with open(out_jsonl, "w", encoding="utf-8") as fout:
        skipped = 0
        for img_id, img_info in images.items():
            img_path = os.path.join(f"data/invoices-8/{split_name}", img_info['file_name'])
            # Get preprocessed image and scale factors
            image, w_scale, h_scale = preprocess_image_for_ocr(img_path, return_scale=True, binarize=False)
            if image is None:
                print(f"[{split_name}] Skipping {img_info['file_name']} (image read error)")
                skipped += 1
                continue

            tokens = ocr_tokens_and_bboxes(image)

            if not tokens:
                print(f"[{split_name}] Skipping {img_info['file_name']} (no OCR tokens)")
                skipped += 1
                continue  # Skip images with no tokens

            # Sort tokens top-to-bottom, left-to-right
            tokens.sort(key=lambda t: (t["position"][0], t["position"][1]))

            # Get annotation regions for this image
            regions = regions_per_image.get(img_id, [])
            if not regions:
                print(f"[{split_name}] Warning: No annotations for {img_info['file_name']}")

            # BIO tagging with scale factors
            labels = bio_tag_tokens(tokens, regions, w_scale=w_scale, h_scale=h_scale, iou_threshold=0.1)

            # Write as JSONL
            fout.write(json.dumps({
                "file_name": img_info['file_name'],
                "tokens": [t["text"] for t in tokens],
                "bboxes": [t["bbox"] for t in tokens],
                "labels": labels
            }, ensure_ascii=False) + "\n")
    print(f"[{split_name}] Conversion complete! Output saved to {out_jsonl}")
    print(f"[{split_name}] Skipped {skipped} images with no OCR tokens.")

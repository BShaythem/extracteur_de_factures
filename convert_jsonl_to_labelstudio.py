import json
import os

# Path to your JSONL and image folder
jsonl_path = "layoutlmv3_train.jsonl"  # Change to your valid/test file as needed
image_dir = os.path.join("dataset", "train")  # Change to "valid" for validation set
output_path = "label_studio_import.json"

# Helper: convert normalized 0-1000 bbox to percent (Label Studio expects percent of image size)
def bbox_to_percent(bbox, img_width=1000, img_height=1000):
    x0, y0, x1, y1 = bbox
    x = x0 / img_width * 100
    y = y0 / img_height * 100
    width = (x1 - x0) / img_width * 100
    height = (y1 - y0) / img_height * 100
    return x, y, width, height

tasks = []
with open(jsonl_path, "r", encoding="utf-8") as f:
    for line in f:
        item = json.loads(line)
        image_path = os.path.join(image_dir, item["file_name"])
        results = []
        for bbox, label in zip(item["bboxes"], item["labels"]):
            # bbox is [x0, y0, x1, y1] in 0-1000 normalized coordinates
            x, y, width, height = bbox_to_percent(bbox)
            results.append({
                "original_width": 1000,
                "original_height": 1000,
                "image_rotation": 0,
                "value": {
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height,
                    "rotation": 0
                },
                "from_name": "label",
                "to_name": "image",
                "type": "rectanglelabels",
                "labels": [label]
            })
        tasks.append({
            "data": {"image": image_path},
            "annotations": [{"result": results}]
        })

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(tasks, f, ensure_ascii=False, indent=2)

print(f"Label Studio import file saved to {output_path}")

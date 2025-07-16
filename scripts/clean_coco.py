import json

with open("annotations_coco.json", "r") as f:
    coco = json.load(f)

def is_valid_ann(ann):
    bbox = ann.get("bbox")
    return (
        isinstance(bbox, list) and len(bbox) == 4 and
        all(isinstance(x, (int, float)) for x in bbox) and
        ann.get("area", 0) > 0 and
        "image_id" in ann and "category_id" in ann
    )

cleaned_annotations = [ann for ann in coco.get("annotations", []) if is_valid_ann(ann)]
coco["annotations"] = cleaned_annotations

# Optionally, remove images with no valid annotations
valid_image_ids = set(ann["image_id"] for ann in cleaned_annotations)
coco["images"] = [img for img in coco.get("images", []) if img["id"] in valid_image_ids]

with open("annotations_coco_cleaned.json", "w") as f:
    json.dump(coco, f, indent=2)

print(f"Cleaned COCO saved as annotations_coco_cleaned.json")
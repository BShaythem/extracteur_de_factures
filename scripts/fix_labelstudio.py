import json
import uuid

INPUT_PATH = "data/invoices/preannotated_labelstudio1.json"
OUTPUT_PATH = "data/invoices/preannotated_labelstudio_fixed1.json"

FROM_NAME = "label"  # Change if your project uses a different name
TO_NAME = "image"
TYPE = "rectanglelabels"

def fix_result(result):
    fixed = []
    for ann in result:
        # Skip empty or malformed
        if not isinstance(ann, dict) or "value" not in ann:
            continue
        value = ann["value"]
        # Skip if labels is missing or empty
        if "labels" not in value or not value["labels"]:
            continue
        # Add required keys
        fixed.append({
            "id": str(uuid.uuid4()),
            "from_name": FROM_NAME,
            "to_name": TO_NAME,
            "type": TYPE,
            "value": value
        })
    return fixed

def main():
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    for item in data:
        # Replace path with URL
        if "data" in item and "image" in item["data"]:
            img_path = item["data"]["image"].replace("\\", "/")
            if img_path.startswith("data/invoices/train/"):
                img_path = img_path.replace("data/invoices/train/", "http://localhost:8081/")
            item["data"]["image"] = img_path
        for ann in item.get("annotations", []):
            ann["result"] = fix_result(ann.get("result", []))

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Cleaned file saved to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
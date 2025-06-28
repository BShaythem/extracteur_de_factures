from roboflow import Roboflow
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("ROBOFLOW_API_KEY")
if not api_key:
    raise ValueError("ROBOFLOW_API_KEY environment variable not set. Please add it to your .env file.")

rf = Roboflow(api_key=api_key)
project = rf.workspace("project627-nnwcu").project("invoice-l9qcj")
dataset = project.version(5).download("coco", location="dataset")
print(f"Data downloaded to: {dataset.location}")

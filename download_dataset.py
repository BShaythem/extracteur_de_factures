from roboflow import Roboflow
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("ROBOFLOW_API_KEY")
if not api_key:
    raise ValueError("ROBOFLOW_API_KEY environment variable not set. Please add it to your .env file.")

rf = Roboflow(api_key=api_key)
project = rf.workspace("roboflow-5gpbq").project("invoice-data-mbpu8")
version = project.version(1)
dataset = version.download("coco")
print(f"Data downloaded to: {dataset.location}")
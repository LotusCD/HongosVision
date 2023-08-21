import json
import os
import time
from dotenv import load_dotenv
from azure.cognitiveservices.vision.customvision.training import CustomVisionTrainingClient
from azure.cognitiveservices.vision.customvision.training.models import ImageFileCreateBatch, ImageFileCreateEntry
from msrest.authentication import ApiKeyCredentials

def with_exponential_backoff(func, max_retries=5, initial_delay=5):
    """Wrapper function to handle rate limits with exponential backoff."""
    retries = 0
    delay = initial_delay
    while retries <= max_retries:
        try:
            return func()
        except Exception as e:
            if "Too Many Requests" in str(e) and retries < max_retries:
                print(f"Rate limit hit. Retrying in {delay} seconds...")
                time.sleep(delay)
                retries += 1
                delay *= 2
            else:
                raise

# Load variables from .env into environment
load_dotenv()

ENDPOINT = os.getenv('ENDPOINT')
training_key = os.getenv('TRAINING_KEY')
project_name = "Hongos_CO"

print("Setting up Azure Custom Vision client...")
credentials = ApiKeyCredentials(in_headers={"Training-key": training_key})
trainer = CustomVisionTrainingClient(ENDPOINT, credentials)

print(f"Creating project: {project_name}...")
project = with_exponential_backoff(lambda: trainer.create_project(project_name))

# Load tags.json and create tags
print("Loading tags from tags.json...")
with open('tags.json', 'r') as f:
    tags_data = json.load(f)

print("Creating tags in Azure Custom Vision...")
tag_objects = {}
for genus_name, taxonomy in tags_data.items():
    for taxon, value in taxonomy.items():
        tag_name = f"{taxon}_{value}"
        if tag_name not in tag_objects:
            print(f"Creating tag: {tag_name}...")
            tag_objects[tag_name] = with_exponential_backoff(lambda: trainer.create_tag(project.id, tag_name))

# Create tags from metadata.json files
base_folder = os.path.abspath("./fungi_images")
for genus_name in os.listdir(base_folder):
    metadata_path = os.path.join(base_folder, genus_name, 'metadata.json')
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    for image_data in metadata.values():
        for taxon, value in image_data.items():
            tag_name = f"{taxon}_{value}"
            if tag_name not in tag_objects:
                print(f"Creating tag: {tag_name}...")
                tag_objects[tag_name] = with_exponential_backoff(lambda: trainer.create_tag(project.id, tag_name))

# Upload images with tags from metadata.json
for genus_name in os.listdir(base_folder):
    folder_path = os.path.join(base_folder, genus_name)
    
    # Check if it's a directory
    if not os.path.isdir(folder_path):
        continue

    metadata_path = os.path.join(folder_path, 'metadata.json')
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)

    # Assuming all images in the folder have the same tags, grab tags from any entry in metadata.json
    sample_image_data = next(iter(metadata.values()))

    image_list = []

    # Get all image files in the folder
    image_files = [f for f in os.listdir(folder_path) if f.endswith('.jpg') and os.path.isfile(os.path.join(folder_path, f))]

    for image_name in image_files:
        image_path = os.path.join(folder_path, image_name)
        
        tag_ids = []
        for taxon, value in sample_image_data.items():
            tag_name = f"{taxon}_{value}"
            tag_ids.append(tag_objects[tag_name].id)

        with open(image_path, "rb") as image_contents:
            image_list.append(ImageFileCreateEntry(name=image_name, contents=image_contents.read(), tag_ids=tag_ids))

    # Bulk upload images for the current folder
    if not image_list:
        print(f"WARNING: No valid images to upload for genus: {genus_name}. Skipping upload.")
        continue

    print(f"Bulk uploading images for genus: {genus_name}...")
    upload_result = with_exponential_backoff(lambda: trainer.create_images_from_files(project.id, ImageFileCreateBatch(images=image_list)))
    if not upload_result.is_batch_successful:
        print(f"Image batch upload failed for {genus_name} folder.")
        for image in upload_result.images:
            print("Image status:", image.status)



print("Script completed!")

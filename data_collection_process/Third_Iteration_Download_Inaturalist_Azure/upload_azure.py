
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
project_name = "Hongos_CO_sample"

print("Setting up Azure Custom Vision client...")
credentials = ApiKeyCredentials(in_headers={"Training-key": training_key})
trainer = CustomVisionTrainingClient(ENDPOINT, credentials)

print(f"Creating project: {project_name}...")
project = with_exponential_backoff(lambda: trainer.create_project(project_name))

print("Loading tags from tags.json...")
with open('tags.json', 'r') as f:
    tags_data = json.load(f)

print("Creating tags in Azure Custom Vision...")
tag_objects = {}
base_folder = os.path.abspath("./fungi_images")

# Only create tags for genera with corresponding folders
for genus_name, taxonomy in tags_data.items():
    if os.path.exists(os.path.join(base_folder, genus_name)):
        # Create a tag for the genus itself
        genus_tag_name = f"genus_{genus_name}"
        if genus_tag_name not in tag_objects:
            print(f"Creating tag: {genus_tag_name}...")
            tag_objects[genus_tag_name] = with_exponential_backoff(lambda: trainer.create_tag(project.id, genus_tag_name))

        for taxon, value in taxonomy.items():
            tag_name = f"{taxon}_{value}"
            if tag_name not in tag_objects:
                print(f"Creating tag: {tag_name}...")
                tag_objects[tag_name] = with_exponential_backoff(lambda: trainer.create_tag(project.id, tag_name))

# The rest of the script remains the same, as it was in the previous version


for genus_name in os.listdir(base_folder):
    genus_folder = os.path.join(base_folder, genus_name)
    
    # Ensure it's a directory
    if not os.path.isdir(genus_folder):
        continue

    metadata_path = os.path.join(genus_folder, 'metadata.json')
    try:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
    except FileNotFoundError:
        print(f"WARNING: No metadata.json found for genus: {genus_name}. Skipping this genus.")
        continue

    sample_image_data = next(iter(metadata.values()))

    # Iterate over the ID folders inside the genus folder
    for id_folder in os.listdir(genus_folder):
        id_folder_path = os.path.join(genus_folder, id_folder)

        # Skip if it's the metadata.json file or if it's not a directory
        if id_folder == 'metadata.json' or not os.path.isdir(id_folder_path):
            continue

        image_list = []

        # Get all image files in the ID folder
        image_files = [f for f in os.listdir(id_folder_path) if f.endswith('.jpeg') and os.path.isfile(os.path.join(id_folder_path, f))]
        print(f"Found {len(image_files)} images in {id_folder_path}")

        for image_name in image_files:
            image_path = os.path.join(id_folder_path, image_name)
            
            tag_ids = []
            genus_tag_name = f"genus_{genus_name}"
            tag_ids.append(tag_objects[genus_tag_name].id)
            for taxon, value in sample_image_data.items():
                tag_name = f"{taxon}_{value}"
                tag_ids.append(tag_objects[tag_name].id)

            try:
                with open(image_path, "rb") as image_contents:
                    image_list.append(ImageFileCreateEntry(name=image_name, contents=image_contents.read(), tag_ids=tag_ids))
            except FileNotFoundError as e:
                print(f"WARNING: File not found: {image_path}. Skipping this image.")
                continue

        # Bulk upload images for the current ID folder
        if not image_list:
            print(f"WARNING: No valid images to upload for ID folder: {id_folder} in genus: {genus_name}. Skipping upload.")
            continue

        print(f"Bulk uploading images for ID folder: {id_folder} in genus: {genus_name}...")
        upload_result = with_exponential_backoff(lambda: trainer.create_images_from_files(project.id, ImageFileCreateBatch(images=image_list)))
        if not upload_result.is_batch_successful:
            print(f"Image batch upload failed for ID folder: {id_folder} in genus: {genus_name} folder.")
            for image in upload_result.images:
                print("Image status:", image.status)
        else:
            print(f"Successfully uploaded {len(image_list)} images for ID folder: {id_folder} in genus: {genus_name}")

print("Script completed!")

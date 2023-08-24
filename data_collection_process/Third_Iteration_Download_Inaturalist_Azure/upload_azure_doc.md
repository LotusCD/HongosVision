
# Azure Custom Vision Image Uploader

This script is designed to automate the process of creating tags and uploading images to Azure's Custom Vision Service. It uses information from a `tags.json` file, metadata files, and the structure of your image directories.

## Prerequisites

1. Azure's `cognitiveservices` Python SDK.
2. A `.env` file containing your Azure endpoint and training key.

## How the Script Works

1. **Setup and Initialization**
    - Loads necessary environment variables from a `.env` file.
    - Initializes the Azure Custom Vision Training Client.

2. **Tag Creation from `tags.json`**
    - The script reads a `tags.json` file. This file should contain genera as keys with their taxonomic ranks as nested dictionaries.
    - For each genus and its taxonomic ranks, the script checks if a corresponding folder exists in the `fungi_images` directory. If it does, tags are created in Azure.

3. **Tag Creation from `metadata.json`**
    - For each genus folder inside `fungi_images`, the script reads its `metadata.json` file.
    - Tags are created in Azure based on the taxonomic ranks present in the metadata.

4. **Image Uploading**
    - For each genus, the script dives into its ID folders.
    - Images inside these folders are associated with tags based on the genus and the metadata.
    - Images are then batch uploaded to Azure with their associated tags.

5. **Error Handling**
    - The script has built-in error handling for rate limits, using an exponential backoff strategy.
    - File not found errors are handled gracefully, with warnings printed to the console.

## Directory Structure

Your `fungi_images` directory should look something like:

```
Amanita
    1718129
        - image1.jpeg
        - image2.jpeg
    172839
        - image1.jpeg
        - image2.jpeg
    metadata.json
Cookeina
    1231
        - image1.jpeg
        - image2.jpeg
    3643
        - image1.jpeg
        - image2.jpeg
    metadata.json
```

Each genus folder contains ID folders with images and a `metadata.json` file.

## Usage

1. Ensure you have the necessary prerequisites.
2. Update your `tags.json` file and ensure your directory structure matches the expected format.
3. Run the script!

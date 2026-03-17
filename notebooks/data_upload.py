"""
Script for Uploading Local Files to Databricks Volume

This script uploads files from a specified local directory to a Databricks volume
using the Databricks REST API.
It reads project configuration settings from a YAML file,
initializes a VolumeLoader instance,
and uploads all files from the source directory to the target volume path
defined in the project configuration.

Main Steps:
-----------
1. Load project configuration from YAML file.
2. Initialize the VolumeLoader utility.
3. Upload all files from the local source directory to the Databricks volume.

Usage:
------
- Configure the source directory and volume path in `project_config.yml`.
- Run the script to upload all files in the specified local folder
to the Databricks volume.

Dependencies:
-------------
- filteredNotFrenzied (for config and ingestion utilities)
- databricks-sdk (for WorkspaceClient)
- PyYAML (for reading YAML config)

Author:
-------
- Maintainer: MMASWK

"""

from filteredNotFrenzied.volume_loader import VolumeLoader

volume_loader = VolumeLoader()
volume_loader.upload_folder_to_volume(
    "data", "/Volumes/dev/datalab_1ai/files/mdpi_papers/"
)

print("Success")

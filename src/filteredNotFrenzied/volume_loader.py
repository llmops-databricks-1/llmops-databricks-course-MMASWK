"""
VolumeLoader Utility for Databricks File Uploads

This module provides the VolumeLoader class, which simplifies uploading files
and images from a local environment
to Databricks File System (DBFS) or Databricks Volumes using the Databricks REST API
and WorkspaceClient.

Features:
---------
- Upload individual files to DBFS or a Databricks volume.
- Upload image objects directly to DBFS.
- Recursively upload all files from a local folder to a specified Databricks volume path.

Typical Usage:
--------------
1. Initialize a VolumeLoader instance.
2. Use `upload_file_to_dbfs` to upload a single file.
3. Use `upload_image_to_dbfs` to upload an image object.
4. Use `upload_folder_to_volume` to upload all files in a folder to a Databricks volume.

Dependencies:
-------------
- databricks-sdk (WorkspaceClient)
- os, io (standard library)

Author:
-------
- Maintainer: MMASWK

"""

import io
import os

from databricks.sdk import WorkspaceClient


class VolumeLoader:
    def __init__(self) -> None:
        """
        Initializes the VolumeLoader instance with a project configuration and
        Databricks credentials.

        Args:
            project_config (ProjectConfig): An instance of the `ProjectConfig` class
            containing project-level settings such as
            catalog name,
            schema name
            and file format.
        """

    def upload_file_to_dbfs(
        self,
        w: WorkspaceClient,
        local_file_path: str,
        dbfs_path: str,
    ) -> None:
        """
        Uploads a single file to Databricks DBFS using the REST API.

        Args:
            local_file_path (str): Path to the local file to upload.
            dbfs_path (str): Path in Databricks DBFS where the file will be uploaded.
        """

        with open(local_file_path, "rb") as file:
            data = file.read()
        binary_data = io.BytesIO(data)

        w.files.upload(dbfs_path, binary_data, overwrite=True)

        print(f"Successfully uploaded {local_file_path} to {dbfs_path}")

    def upload_image_to_dbfs(
        self,
        w: WorkspaceClient,
        image: io.BytesIO,
        dbfs_path: str,
    ) -> None:
        """
        Uploads a single file to Databricks DBFS using the REST API.

        Args:
            local_file_path (str): Path to the local file to upload.
            dbfs_path (str): Path in Databricks DBFS where the file will be uploaded.
        """

        w.files.upload(dbfs_path, image, overwrite=True)
        print(f"Successfully uploaded to {dbfs_path}")

    def upload_folder_to_volume(self, local_folder: str, volume_path: str) -> None:
        """
        Uploads files from a local folder to a Databricks volume using the REST API.

        Args:
            local_folder (str): Path to the local folder containing files to upload.
            volume_path (str): Path to the Databricks volume where files will be uploaded.
        """

        w = WorkspaceClient()
        for root, _dirs, files in os.walk(local_folder):
            for file in files:
                local_file_path = os.path.join(root, file)
                # relative_path = os.path.relpath(local_file_path, local_folder)
                dbfs_path = os.path.join(volume_path, file)
                print(f"Uploading {local_file_path} to {dbfs_path}")
                self.upload_file_to_dbfs(w, local_file_path, dbfs_path)

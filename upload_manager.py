import logging
import os
from typing import Literal, Optional
from fastapi import File, UploadFile
from openai import AsyncOpenAI

PurposeType = Literal["assistants"]

class UploadManager:
    def __init__(self, client: AsyncOpenAI):
        self.client = client

    async def upload_files_from_dir_async(self, directory, purpose: PurposeType = "assistants"):
        if not os.path.isdir(directory):
            return []

        uploaded_file_ids = []

        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            if os.path.isfile(filepath):
                filename = os.path.basename(filepath)
                existing_file_id = await self.find_file_id_async(filename)
                if existing_file_id:
                    uploaded_file_ids.append(existing_file_id)
                    continue
                file = open(filepath, "rb")
                file_response = await self.client.files.create(file=(filename, bytes(file.read())), purpose=purpose)
                if file_response is not None:
                    uploaded_file_ids.append(file_response.id)

        return uploaded_file_ids
        
    async def find_file_id_async(self, filename):
        response = await self.client.files.list()
        for file in response.data:
            if file.filename == filename:
                return file.id
        return None
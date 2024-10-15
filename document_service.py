import json
import logging
from openai import AsyncOpenAI
from thread_manager import ThreadManager

class DocumentService:
    def __init__(self, client: AsyncOpenAI, assistant_id: str):
        self.client = client
        self.assistant_id = assistant_id
        self.document_thread_manager = None

    async def prepare_thread_async(self, thread_id=None, initialize_thread=True):
        self.document_thread_manager = ThreadManager(client=self.client, assistant_id=self.assistant_id)
        if initialize_thread:
            await self.document_thread_manager.get_thread_async(thread_id)

    async def process_query_async(self, message, thread_id=None):
        try:
            await self.prepare_thread_async(thread_id)
            thread = self.document_thread_manager.thread
            
            thread_id = thread.id

            _ = await self.document_thread_manager.add_message_to_thread_async(role="user", content=message)

            async for event in self.document_thread_manager.get_thread_stream_async():
                if event.event == "thread.message.completed":
                    yield f'data: {json.dumps({"content": event.data.content[0].text, "thread_id": thread.id, "last_message": True })}\n\n'
                elif event.event == "thread.message.delta":
                    yield f'data: {json.dumps({"content": event.data.delta.content[0].text.value, "thread_id": thread.id, "last_message": False })}\n\n'
            
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            raise e
        
    async def messages_list_async(self, thread_id):
        try:
            await self.prepare_thread_async(thread_id)
            return await self.document_thread_manager.messages_list_async()
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            return []
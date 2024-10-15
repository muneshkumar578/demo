import logging
import json
from typing import List
from openai import AsyncOpenAI, AsyncAssistantEventHandler
from openai.types.beta.threads import Message
from openai.types.beta.threads import RequiredActionFunctionToolCall

class ThreadManager:
    def __init__(self, client: AsyncOpenAI, assistant_id):
        self.client = client
        self.assistant_id = assistant_id
        self.thread = None
        self.run = None

    async def get_thread_async(self, thread_id=None):
        self.thread = await self.client.beta.threads.retrieve(thread_id) if thread_id else await self.client.beta.threads.create()
        return self.thread
    
    async def add_message_to_thread_async(self, role, content):
        message = await self.client.beta.threads.messages.create(
            thread_id=self.thread.id,
            role=role,
            content=content
        )
        return message.id
    
    async def get_thread_stream_async(self):
        try:
            async with self.client.beta.threads.runs.stream(
                thread_id=self.thread.id,
                assistant_id=self.assistant_id,
            ) as stream:
                async for result in self.handle_stream_async(stream):
                    yield result
                await stream.until_done()
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            raise e
        
    async def handle_stream_async(self, stream: AsyncAssistantEventHandler):
        try:
            async for event in stream:
                if event.event == 'thread.message.delta' and event.data.delta.content:
                    yield event
                elif event.event == 'thread.run.requires_action':
                    run_id = event.data.id
                    tool_outputs = self.handle_requires_action(event.data.required_action.submit_tool_outputs.tool_calls)
                    async with self.client.beta.threads.runs.submit_tool_outputs_stream(
                        thread_id=self.thread.id,
                        run_id=run_id,
                        tool_outputs=tool_outputs
                    ) as new_stream:
                        async for result in self.handle_stream_async(new_stream):
                            yield result
                elif event.event == "thread.message.completed":
                    has_annaotation = bool(event.data.content[0].text.annotations)
                    if has_annaotation:
                        event.data.content[0].text = await self.process_annotations_async(event.data)
                        yield event
                elif event.event == 'thread.run.completed':
                    break
                
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            raise e
        
    async def process_annotations_async(self, message: Message):
        message_content = message.content[0].text
        annotations = message_content.annotations
        citations = []
        
        for index, annotation in enumerate(annotations):
            message_content.value = message_content.value.replace(annotation.text, f' [{index+1}]')
        
            if (file_citation := getattr(annotation, 'file_citation', None)):
                cited_file = await self.client.files.retrieve(file_citation.file_id)
                citations.append(f'[{index+1}] {cited_file.filename}')
        
        message_content.value += '\n\n' + '\n\n'.join(citations)
        return message_content.value
    
    async def messages_list_async(self):
        messages_list = []
        messages = await self.client.beta.threads.messages.list(thread_id=self.thread.id)
        for msg in messages.data:
            message = {}
            message["role"] = msg.role
            message["content"] = await self.process_annotations_async(msg)
            messages_list.append(message) 
        return messages_list
    
    def handle_requires_action(self, tool_calls: List[RequiredActionFunctionToolCall]):
        tool_outputs = []
        for tool in tool_calls:
            match tool.function.name:
                case "get_accessible_documents":
                    function_args = json.loads(tool.function.arguments)
                    user_id = function_args.get("user_id", None)
                    document_list = self.get_accessible_documents(user_id)

                    tool_outputs.append({
                        "tool_call_id": tool.id,
                        "output": json.dumps(document_list)
                    })
        
        return tool_outputs


    def get_accessible_documents(self, user_id):
        print(f"Fetching documents for user: {user_id}")
        mock_document_access_list = [
                {
                    "doc_id": "doc1",
                    "title": "Project Requirements",
                    "last_accessed": "2024-10-08"
                },
                {
                    "doc_id": "doc2",
                    "title": "Technical Specifications",
                    "last_accessed": "2024-10-09"
                }
            ]
        return mock_document_access_list

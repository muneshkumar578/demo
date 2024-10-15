import logging
from fastapi import FastAPI, File, UploadFile
from starlette.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi.responses import StreamingResponse
from assistant_manager import AssistantManager
from document_service import DocumentService
from pydantic import BaseModel

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)


class Query(BaseModel):
    query: str
    thread_id: str




@asynccontextmanager
async def lifespan(api: FastAPI):
    

    document_assistant = AssistantManager(update_assistant_flag=True)
    await document_assistant.prepare_assistant_async()
    api.state.document_assistant = document_assistant

    document_gpt_service: DocumentService = DocumentService(client=document_assistant.client,
        assistant_id=document_assistant.assistant.id)
    api.state.document_gpt_service = document_gpt_service



    yield
    




api = FastAPI(lifespan=lifespan)



@api.post("/query")
async def query(query: Query):
    document_gpt_service: DocumentService = api.state.document_gpt_service

    async def get_streamed_response():
        async for event in document_gpt_service.process_query_async(query.query, query.thread_id):
            yield event

    return StreamingResponse(get_streamed_response(), media_type="text/event-stream")


@api.get("/conversation/{thread_id}")
async def get_conversation_messages_by_thread_id(thread_id: str):
    document_gpt_service: DocumentService = api.state.document_gpt_service
    return await document_gpt_service.messages_list_async(thread_id)
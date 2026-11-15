from contextlib import asynccontextmanager
from datetime import datetime
import hmac
import logging
import os
from pathlib import Path
from uuid import UUID

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pymongo.errors import PyMongoError
from starlette.concurrency import run_in_threadpool

from backend.schemas import Chunk, Completion, MAX_BODY_BYTES, Recording
from backend.storage import Conflict, MongoStore, NotFound
from backend.eeg_stream.speech import DemoSpeechSelection, synthesize_demo_speech


logger = logging.getLogger(__name__)
bearer = HTTPBearer(auto_error=False)


class BodyLimit:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        messages = []
        size = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > MAX_BODY_BYTES:
                response = JSONResponse({"detail": "Request body exceeds 1 MiB"}, status_code=413)
                await response(scope, receive, send)
                return
            messages.append(message)
            if not message.get("more_body", False):
                break
        iterator = iter(messages)

        async def replay():
            return next(iterator, {"type": "http.request", "body": b"", "more_body": False})

        await self.app(scope, replay, send)


def create_app(store=None, token: str | None = None, owner: str | None = None):
    load_dotenv(Path(__file__).with_name(".env.local"))
    load_dotenv(Path(__file__).with_name(".env"))
    origins = [
        origin.strip() for origin in os.environ.get(
            "EEG_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",") if origin.strip()
    ]
    if "*" in origins:
        raise ValueError("EEG_ALLOWED_ORIGINS must list explicit browser origins")

    @asynccontextmanager
    async def lifespan(app):
        app.state.token = token or os.environ.get("EEG_API_TOKEN")
        app.state.owner = owner or os.environ.get("EEG_OWNER_ID")
        if not app.state.token or len(app.state.token) < 32 or not app.state.owner:
            raise RuntimeError("Configure an EEG_API_TOKEN of at least 32 characters and EEG_OWNER_ID")
        if store is None:
            uri = os.environ.get("MONGODB_URI")
            if not uri or "<" in uri or "REPLACE_" in uri or "CLUSTER_HOST" in uri:
                raise RuntimeError("Configure MONGODB_URI locally; do not use placeholder credentials")
            app.state.store = MongoStore(uri, os.environ.get("MONGODB_DATABASE", "eeg"))
        else:
            app.state.store = store
        try:
            await run_in_threadpool(app.state.store.start)
            yield
        except PyMongoError as exc:
            logger.error("MongoDB lifecycle failure (%s)", type(exc).__name__)
            raise RuntimeError("MongoDB initialization failed; check local credentials/network") from None
        finally:
            await run_in_threadpool(app.state.store.close)

    app = FastAPI(title="NeuronVision cloud API", version="1", lifespan=lifespan)
    app.add_middleware(BodyLimit)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )

    def authorized(request: Request,
                   credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
        if credentials is None or not hmac.compare_digest(
            credentials.credentials.encode("utf-8"), request.app.state.token.encode("utf-8")
        ):
            raise HTTPException(401, "Valid ingestion token required")
        return request.app.state.owner

    def speech_authorized(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    ):
        speech_token = os.environ.get("EEG_DEMO_TOKEN", "")
        if len(speech_token) < 32 or speech_token.startswith("REPLACE_"):
            raise HTTPException(503, "Configure the server's EEG_DEMO_TOKEN for demo speech")
        if credentials is None or not hmac.compare_digest(
            credentials.credentials.encode("utf-8"), speech_token.encode("utf-8")
        ):
            raise HTTPException(401, "A valid demo speech access token is required")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/api/demo/speech")
    def demo_speech(selection: DemoSpeechSelection, access=Depends(speech_authorized)):
        return Response(
            content=synthesize_demo_speech(selection.path),
            media_type="audio/mpeg",
            headers={"Cache-Control": "no-store"},
        )

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        errors = [{"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]}
                  for error in exc.errors()]
        return JSONResponse({"detail": errors}, status_code=422)

    @app.exception_handler(Conflict)
    async def conflict(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(NotFound)
    async def not_found(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=404)

    @app.exception_handler(ValueError)
    async def bad_input(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=422)

    @app.exception_handler(PyMongoError)
    async def database_failure(request, exc):
        logger.error("MongoDB operation failed (%s)", type(exc).__name__)
        return JSONResponse({"detail": "Database operation failed; retry safely"},
                            status_code=503, headers={"Retry-After": "1"})

    @app.post("/v1/recordings")
    def create_recording(recording: Recording, request: Request, owner=Depends(authorized)):
        return request.app.state.store.create(recording, owner)

    @app.post("/v1/recordings/{recording_id}/chunks")
    def append_chunk(recording_id: UUID, chunk: Chunk, request: Request, owner=Depends(authorized)):
        return request.app.state.store.append(str(recording_id), owner, chunk)

    @app.post("/v1/recordings/{recording_id}/complete")
    def complete(recording_id: UUID, expected: Completion, request: Request, owner=Depends(authorized)):
        return request.app.state.store.complete(str(recording_id), owner, expected)

    @app.get("/v1/recordings")
    def recordings(request: Request, after: str = "", limit: int = Query(20, ge=1, le=100),
                   owner=Depends(authorized)):
        return request.app.state.store.recordings(owner, after, limit)

    @app.get("/v1/recordings/{recording_id}/samples")
    def samples(recording_id: UUID, request: Request, after: int = Query(-1, ge=-1),
                limit: int = Query(500, ge=1, le=2000), start: datetime | None = None,
                end: datetime | None = None, owner=Depends(authorized)):
        for bound in (start, end):
            if bound is not None and (bound.tzinfo is None or bound.utcoffset() is None):
                raise HTTPException(422, "Time bounds require a timezone")
        if start is not None and end is not None and start >= end:
            raise HTTPException(422, "start must precede end")
        return request.app.state.store.samples(str(recording_id), owner, after, limit, start, end)

    return app


app = create_app()

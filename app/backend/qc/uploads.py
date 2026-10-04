"""Persistent, owner-bound upload staging. One photo per request; atomic vehicle commit."""

import json
import shutil
import threading
import time
from types import SimpleNamespace
from uuid import UUID

from fastapi import File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from .db import Shoot, uid
from .media import MAX_BATCH_BYTES, prepare_image
from .schemas import ImportInput


class StartBatch(BaseModel):
    metadata: ImportInput
    count: int = Field(ge=1, le=200)


def register_upload_routes(app, factory, data, import_batch):
    root = data / "upload-staging"
    root.mkdir(exist_ok=True)
    lock = threading.RLock()  # App runs one worker; only staging writes use this lock.
    ttl = 24 * 60 * 60

    def write(folder, state):
        temp = folder / "state.new"
        temp.write_text(json.dumps(state), encoding="utf-8")
        temp.replace(folder / "state.json")

    def cleanup():
        for folder in root.iterdir():
            if not folder.is_dir():
                continue
            state_file = folder / "state.json"
            if time.time() - folder.stat().st_mtime > ttl and not state_file.exists():
                shutil.rmtree(folder)
            elif state_file.exists():
                state = json.loads(state_file.read_text(encoding="utf-8"))
                if time.time() - state["created"] > ttl:
                    shutil.rmtree(folder)

    def owned(batch_id, request):
        folder = root / str(batch_id)
        path = folder / "state.json"
        if not path.is_file():
            raise HTTPException(404, "Upload expired or was cancelled. Start the upload again.")
        state = json.loads(path.read_text(encoding="utf-8"))
        if state["owner"] != request.state.user:
            raise HTTPException(404, "Upload not found.")
        if time.time() - state["created"] > ttl:
            raise HTTPException(410, "Upload expired. Start the upload again.")
        return folder, state

    with lock:
        cleanup()

    @app.post("/api/uploads", status_code=201)
    def start(body: StartBatch, request: Request):
        if body.metadata.shot_types is not None and len(body.metadata.shot_types) != body.count:
            raise HTTPException(422, "One shot type is required for each photo.")
        with lock:
            cleanup()
            pending = [
                p
                for p in root.glob("*/state.json")
                if not json.loads(p.read_text(encoding="utf-8")).get("result")
            ]
            if len(pending) >= 8:
                raise HTTPException(
                    409, "Eight uploads are already pending. Finish or cancel one before starting another."
                )
            batch_id = uid()
            folder = root / batch_id
            folder.mkdir()
            (folder / "tmp").mkdir()
            state = {
                "owner": request.state.user,
                "created": time.time(),
                "count": body.count,
                "metadata": body.metadata.model_dump(mode="json"),
                "photos": {},
                "total": 0,
            }
            write(folder, state)
            return {"id": batch_id}

    @app.get("/api/uploads/{batch_id}")
    def status(batch_id: UUID, request: Request):
        with lock:
            _, state = owned(batch_id, request)
            return {"received": [int(i) for i in state["photos"]], "result": state.get("result")}

    @app.put("/api/uploads/{batch_id}/photos/{position}")
    def photo(batch_id: UUID, position: int, request: Request, file: UploadFile = File(...)):
        try:
            with lock:
                folder, state = owned(batch_id, request)
                if state.get("result") or not 0 <= position < state["count"]:
                    raise HTTPException(409, "This upload cannot accept that photo.")
                key = str(position)
                if key in state["photos"]:
                    return {"received": position}  # Safe retry after a lost acknowledgement.
                photo_id = uid()
                try:
                    details, paths = prepare_image(file, photo_id, folder)
                except ValueError as exc:
                    raise HTTPException(422, str(exc)) from exc
                if state["total"] + details["byte_size"] > MAX_BATCH_BYTES:
                    for path in paths:
                        path.unlink(missing_ok=True)
                    raise HTTPException(422, "One shoot must be 1 GB or smaller.")
                state["photos"][key] = {
                    "photo_id": photo_id,
                    "details": details,
                    "filename": (file.filename or "photo").replace("\\", "/").split("/")[-1][:255],
                }
                state["total"] += details["byte_size"]
                try:
                    write(folder, state)
                except Exception:
                    for path in paths:
                        path.unlink(missing_ok=True)
                    raise
                return {"received": position}
        finally:
            file.file.close()

    @app.post("/api/uploads/{batch_id}/complete", status_code=201)
    def complete(batch_id: UUID, request: Request):
        with lock:
            folder, state = owned(batch_id, request)
            if state.get("result"):
                return state["result"]
            if len(state["photos"]) != state["count"]:
                raise HTTPException(409, "Wait until every photo has uploaded.")
            # Recover a successful DB commit even if the process stopped before saving its receipt.
            with factory(info={"include_deleted": True}) as session:
                existing = session.get(Shoot, str(batch_id))
            if existing:
                result = {"id": existing.id, "status": existing.status, "photo_count": state["count"]}
            else:
                prepared = [{**state["photos"][str(i)], "root": folder} for i in range(state["count"])]
                result = import_batch(
                    ImportInput(**state["metadata"]),
                    [SimpleNamespace(filename=p["filename"]) for p in prepared],
                    prepared,
                    str(batch_id),
                )
            state["result"] = result
            write(folder, state)
            for name in ("originals", "thumbnails", "tmp"):
                shutil.rmtree(folder / name, ignore_errors=True)
            return result

    @app.delete("/api/uploads/{batch_id}")
    def cancel(batch_id: UUID, request: Request):
        with lock:
            folder, state = owned(batch_id, request)
            if state.get("result"):
                raise HTTPException(409, "Vehicle already submitted. Use its Trash controls instead.")
            # A commit without a receipt must not be described as cancellation.
            with factory(info={"include_deleted": True}) as session:
                if session.get(Shoot, str(batch_id)):
                    raise HTTPException(409, "Vehicle already submitted. Refresh the library.")
            shutil.rmtree(folder)
            return {"status": "cancelled"}

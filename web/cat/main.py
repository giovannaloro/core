import traceback

from fastapi import FastAPI, WebSocket, UploadFile, BackgroundTasks
from cat.utils import log
from cat.rabbit_hole import (  # TODO: should be moved inside the cat as a method?
    ingest_file,
)
from cat.looking_glass import CheshireCat
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

#       ^._.^
#
# loads Cat and plugins
ccat = CheshireCat(verbose=True)

# API endpoints
cheshire_cat_api = FastAPI()


# server status
@cheshire_cat_api.get("/")
async def home():
    return {"status": "We're all mad here, dear!"}


# main loop via websocket
@cheshire_cat_api.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            # message received from user
            user_message = await websocket.receive_text()

            # get response from the cat
            cat_message = ccat(user_message)

            # send output to user
            await websocket.send_json(cat_message)

    except Exception as e:  # WebSocketDisconnect as e:
        log(e)
        traceback.print_exc()

        # send error to user
        await websocket.send_json(
            {
                "error": True,
                "code": type(e).__name__,
            }
        )


# receive files via endpoint
# TODO: should we receive files also via websocket?
@cheshire_cat_api.post("/rabbithole/")
async def rabbithole_upload_endpoint(
    file: UploadFile, background_tasks: BackgroundTasks
):
    log(file.content_type)

    # list of admitted MIME types
    admitted_mime_types = ["text/plain", "application/pdf"]

    # check id MIME type of uploaded file is supported
    if file.content_type not in admitted_mime_types:
        return JSONResponse(
            status_code=422,
            content={
                "detail": f'MIME type {file.content_type} not supported. Admitted types: {" - ".join(admitted_mime_types)}'
            },
        )

    # upload file to long term memory, in the background
    background_tasks.add_task(ingest_file, file, ccat)

    # reply to client
    return {
        "filename": file.filename,
        "content-type": file.content_type,
        "info": "File is being ingested asynchronously.",
    }


# error handling
@cheshire_cat_api.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )
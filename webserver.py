from starlette.applications import Starlette
from starlette.responses import Response, JSONResponse, FileResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
import requests
import os
import json
import aiofiles
import uvicorn
from PIL import Image
from io import BytesIO


async def current_image(request):
    r = requests.get(request.query_params['url'], allow_redirects=True)
    im = Image.open(BytesIO(r.content))
    im.thumbnail((500, 500), Image.ANTIALIAS)
    buf = BytesIO()
    im.save(buf, "JPEG")
    return Response(buf.getvalue(), media_type='image/jpeg')


async def homepage(request):
    return FileResponse('static/index.html')


async def current_state(request):
    if (os.path.exists('current_image_stats.json')):
        with open('current_image_stats.json', 'r') as f:
            return JSONResponse(json.load(f))
    else:
        return Response(status_code=404)


middleware = [
    Middleware(CORSMiddleware, allow_origins=["*"],
               allow_credentials=True,
               allow_methods=["*"],
               allow_headers=["*"], )
]

app = Starlette(debug=False, routes=[
    Route('/', homepage),
    Route('/get_image', current_image),
    Route('/state', current_state),
    Mount('/static', app=StaticFiles(directory='static'), name="static"),
], middleware=middleware)

if __name__ == "__main__":
    uvicorn.run("webserver:app", host="0.0.0.0", port=8000, log_level="info")

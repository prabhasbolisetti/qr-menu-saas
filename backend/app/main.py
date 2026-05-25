from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from app.routers import (
    auth,
    public,
    owner,
    super_admin
)

app = FastAPI(
    title="QR Menu API",
    version="1.0.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router)

app.include_router(public.router)

app.include_router(owner.router)

app.include_router(super_admin.router)


@app.get("/")
def root():

    return {
        "message": "QR Menu API Running"
    }

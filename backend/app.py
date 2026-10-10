from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import user_routes, ai_routes, auth_routes, nutrition_routes
from core.config import settings

app = FastAPI(
    title="AI Fitness Coach API",
    description="Biomechanical Fitness Tracking & Form Correction API for SIH26196",
    version="1.0.0"
)

# Enable CORS for Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_routes.router)
app.include_router(ai_routes.router)
app.include_router(auth_routes.router)
app.include_router(nutrition_routes.router)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "app": "AI Fitness Coach API (SIH26196)",
        "privacy": "Zero video/image data transmitted to server"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=settings.PORT, reload=True)

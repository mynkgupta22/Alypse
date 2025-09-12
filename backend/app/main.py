import uvicorn
from fastapi import FastAPI
from app.routes.user_controller import router

app = FastAPI(
    title="User Management API",
    description="API for managing users with soft delete",
    version="1.0.0"
)

# Register routers
app.include_router(router)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app="app.main:app", host="0.0.0.0", port=8000, reload=True)

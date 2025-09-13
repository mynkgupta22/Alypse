import uvicorn
from fastapi import FastAPI
from app.routes.user_controller import router
from app.core.database import async_engine, Base
import asyncio


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

@app.on_event("startup")
async def on_startup():
    async with async_engine.begin() as conn:
        # ⚠️ optional: drop before creating
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("✅ All tables created automatically!")

if __name__ == "__main__":
    uvicorn.run(app="app.main:app", host="0.0.0.0", port=8000, reload=True)

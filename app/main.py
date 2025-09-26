from fastapi import FastAPI
from app.db.database import Base, engine
from app.api.users.routers.user import router as users_router
from app.api.users.routers.auth_routes import router as auth_router  # ✅ correct import
from app.api.items.routes.item import router as items_router
from app.api.dashboard.routes import router as dashboard_router
from app.api.dashboard.webhooks import router as integrations_router

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Teamiq Backend")

# Mount routers under /api/v1
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(items_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(integrations_router, prefix="/api/v1")

@app.get("/")
def root():
    return {"message": "Welcome to Teamiq Backend"}
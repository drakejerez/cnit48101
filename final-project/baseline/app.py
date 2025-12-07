from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse
import httpx
import os

app = FastAPI(title="Application Service")

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8081")
DB_SERVICE_URL = os.getenv("DB_SERVICE_URL", "http://localhost:8082")

@app.get("/")
def root():
    return {"message": "Application Service", "status": "running"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/api/data")
async def create_data(data: dict, authorization: str = Header(None)):
    """Create data entry - requires authentication"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    # Validate token with auth service
    async with httpx.AsyncClient() as client:
        try:
            auth_response = await client.post(
                f"{AUTH_SERVICE_URL}/validate",
                headers={"Authorization": authorization},
                timeout=5.0
            )
            if auth_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid token")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Auth service unavailable")
    
    # Store data in DB service
    async with httpx.AsyncClient() as client:
        try:
            db_response = await client.post(
                f"{DB_SERVICE_URL}/store",
                json=data,
                headers={"Authorization": authorization},
                timeout=5.0
            )
            if db_response.status_code != 200:
                raise HTTPException(status_code=500, detail="Database operation failed")
            return db_response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Database service unavailable")

@app.get("/api/data/{item_id}")
async def get_data(item_id: str, authorization: str = Header(None)):
    """Retrieve data entry - requires authentication"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    # Validate token with auth service
    async with httpx.AsyncClient() as client:
        try:
            auth_response = await client.post(
                f"{AUTH_SERVICE_URL}/validate",
                headers={"Authorization": authorization},
                timeout=5.0
            )
            if auth_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid token")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Auth service unavailable")
    
    # Retrieve data from DB service
    async with httpx.AsyncClient() as client:
        try:
            db_response = await client.get(
                f"{DB_SERVICE_URL}/retrieve/{item_id}",
                headers={"Authorization": authorization},
                timeout=5.0
            )
            if db_response.status_code == 404:
                raise HTTPException(status_code=404, detail="Item not found")
            if db_response.status_code != 200:
                raise HTTPException(status_code=500, detail="Database operation failed")
            return db_response.json()
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Database service unavailable")

@app.get("/api/preset/{preset_id}")
async def get_preset_data(preset_id: str, authorization: str = Header(None)):
    """Retrieve preset data items - requires authentication"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    # Validate token with auth service
    async with httpx.AsyncClient() as client:
        try:
            auth_response = await client.post(
                f"{AUTH_SERVICE_URL}/validate",
                headers={"Authorization": authorization},
                timeout=5.0
            )
            if auth_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid token")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Auth service unavailable")
    
    # Preset data mappings
    preset_data = {
        "welcome": {"message": "Welcome to the microservices application", "version": "1.0"},
        "status": {"services": ["app", "auth", "db"], "status": "operational"},
        "info": {"description": "This is a microservices demo with OpenTelemetry", "author": "CNIT48101 Team"}
    }
    
    if preset_id in preset_data:
        return {"preset_id": preset_id, "data": preset_data[preset_id]}
    else:
        raise HTTPException(status_code=404, detail=f"Preset '{preset_id}' not found. Available: {list(preset_data.keys())}")

@app.get("/api/presets")
async def list_presets(authorization: str = Header(None)):
    """List all available preset data - requires authentication"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    # Validate token with auth service
    async with httpx.AsyncClient() as client:
        try:
            auth_response = await client.post(
                f"{AUTH_SERVICE_URL}/validate",
                headers={"Authorization": authorization},
                timeout=5.0
            )
            if auth_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid token")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Auth service unavailable")
    
    return {
        "available_presets": ["welcome", "status", "info"],
        "description": "Use /api/preset/{preset_id} to retrieve specific preset data"
    }

@app.post("/api/seed")
async def seed_preset_data(authorization: str = Header(None)):
    """Seed database with preset data - requires authentication"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    # Validate token with auth service
    async with httpx.AsyncClient() as client:
        try:
            auth_response = await client.post(
                f"{AUTH_SERVICE_URL}/validate",
                headers={"Authorization": authorization},
                timeout=5.0
            )
            if auth_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid token")
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Auth service unavailable")
    
    # Seed data
    seed_items = [
        {"name": "Sample Item 1", "type": "test", "value": 100},
        {"name": "Sample Item 2", "type": "demo", "value": 200},
        {"name": "Sample Item 3", "type": "example", "value": 300}
    ]
    
    stored_ids = []
    async with httpx.AsyncClient() as client:
        for item in seed_items:
            try:
                db_response = await client.post(
                    f"{DB_SERVICE_URL}/store",
                    json=item,
                    headers={"Authorization": authorization},
                    timeout=5.0
                )
                if db_response.status_code == 200:
                    stored_ids.append(db_response.json()["id"])
            except httpx.RequestError:
                pass
    
    return {
        "status": "seeded",
        "items_created": len(stored_ids),
        "item_ids": stored_ids
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)



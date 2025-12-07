from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse
import httpx
import os
import time
from opentelemetry import trace
from otel_instrumentation import instrument_fastapi

app = FastAPI(title="Application Service")

# Setup OpenTelemetry
tracer, meter, request_counter, request_duration = instrument_fastapi(app, "app-service")

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8081")
DB_SERVICE_URL = os.getenv("DB_SERVICE_URL", "http://localhost:8082")

@app.get("/")
def root():
    return {"message": "Application Service", "status": "running"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/api/data")
async def create_data(data: dict, authorization: str = Header(None), request: Request = None):
    """Create data entry - requires authentication"""
    start_time = time.time()
    request_counter.add(1, {"method": "POST", "endpoint": "/api/data"})
    
    with tracer.start_as_current_span("app.create_data") as span:
        span.set_attribute("http.method", "POST")
        span.set_attribute("http.route", "/api/data")
        
        if not authorization:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Missing authorization"))
            raise HTTPException(status_code=401, detail="Missing authorization header")
        
        # Validate token with auth service
        with tracer.start_as_current_span("app.validate_token") as auth_span:
            auth_span.set_attribute("service", "auth-service")
            async with httpx.AsyncClient() as client:
                try:
                    auth_response = await client.post(
                        f"{AUTH_SERVICE_URL}/validate",
                        headers={"Authorization": authorization},
                        timeout=5.0
                    )
                    if auth_response.status_code != 200:
                        auth_span.set_status(trace.Status(trace.StatusCode.ERROR, "Invalid token"))
                        span.set_status(trace.Status(trace.StatusCode.ERROR, "Invalid token"))
                        raise HTTPException(status_code=401, detail="Invalid token")
                except httpx.RequestError as e:
                    auth_span.set_status(trace.Status(trace.StatusCode.ERROR, "Auth service unavailable"))
                    span.set_status(trace.Status(trace.StatusCode.ERROR, "Auth service unavailable"))
                    raise HTTPException(status_code=503, detail="Auth service unavailable")
        
        # Store data in DB service
        with tracer.start_as_current_span("app.store_data") as db_span:
            db_span.set_attribute("service", "db-service")
            async with httpx.AsyncClient() as client:
                try:
                    db_response = await client.post(
                        f"{DB_SERVICE_URL}/store",
                        json=data,
                        headers={"Authorization": authorization},
                        timeout=5.0
                    )
                    if db_response.status_code != 200:
                        db_span.set_status(trace.Status(trace.StatusCode.ERROR, "Database operation failed"))
                        span.set_status(trace.Status(trace.StatusCode.ERROR, "Database operation failed"))
                        raise HTTPException(status_code=500, detail="Database operation failed")
                    result = db_response.json()
                    span.set_attribute("item.id", result.get("id", ""))
                    duration = time.time() - start_time
                    request_duration.record(duration, {"method": "POST", "endpoint": "/api/data", "status": "200"})
                    return result
                except httpx.RequestError as e:
                    db_span.set_status(trace.Status(trace.StatusCode.ERROR, "Database service unavailable"))
                    span.set_status(trace.Status(trace.StatusCode.ERROR, "Database service unavailable"))
                    raise HTTPException(status_code=503, detail="Database service unavailable")

@app.get("/api/data/{item_id}")
async def get_data(item_id: str, authorization: str = Header(None), request: Request = None):
    """Retrieve data entry - requires authentication"""
    start_time = time.time()
    request_counter.add(1, {"method": "GET", "endpoint": "/api/data/{id}"})
    
    with tracer.start_as_current_span("app.get_data") as span:
        span.set_attribute("http.method", "GET")
        span.set_attribute("http.route", "/api/data/{item_id}")
        span.set_attribute("item.id", item_id)
        
        if not authorization:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Missing authorization"))
            raise HTTPException(status_code=401, detail="Missing authorization header")
        
        # Validate token with auth service
        with tracer.start_as_current_span("app.validate_token") as auth_span:
            auth_span.set_attribute("service", "auth-service")
            async with httpx.AsyncClient() as client:
                try:
                    auth_response = await client.post(
                        f"{AUTH_SERVICE_URL}/validate",
                        headers={"Authorization": authorization},
                        timeout=5.0
                    )
                    if auth_response.status_code != 200:
                        auth_span.set_status(trace.Status(trace.StatusCode.ERROR, "Invalid token"))
                        span.set_status(trace.Status(trace.StatusCode.ERROR, "Invalid token"))
                        raise HTTPException(status_code=401, detail="Invalid token")
                except httpx.RequestError:
                    auth_span.set_status(trace.Status(trace.StatusCode.ERROR, "Auth service unavailable"))
                    span.set_status(trace.Status(trace.StatusCode.ERROR, "Auth service unavailable"))
                    raise HTTPException(status_code=503, detail="Auth service unavailable")
        
        # Retrieve data from DB service
        with tracer.start_as_current_span("app.retrieve_data") as db_span:
            db_span.set_attribute("service", "db-service")
            async with httpx.AsyncClient() as client:
                try:
                    db_response = await client.get(
                        f"{DB_SERVICE_URL}/retrieve/{item_id}",
                        headers={"Authorization": authorization},
                        timeout=5.0
                    )
                    if db_response.status_code == 404:
                        db_span.set_status(trace.Status(trace.StatusCode.ERROR, "Item not found"))
                        span.set_status(trace.Status(trace.StatusCode.ERROR, "Item not found"))
                        raise HTTPException(status_code=404, detail="Item not found")
                    if db_response.status_code != 200:
                        db_span.set_status(trace.Status(trace.StatusCode.ERROR, "Database operation failed"))
                        span.set_status(trace.Status(trace.StatusCode.ERROR, "Database operation failed"))
                        raise HTTPException(status_code=500, detail="Database operation failed")
                    result = db_response.json()
                    duration = time.time() - start_time
                    request_duration.record(duration, {"method": "GET", "endpoint": "/api/data/{id}", "status": "200"})
                    return result
                except httpx.RequestError:
                    db_span.set_status(trace.Status(trace.StatusCode.ERROR, "Database service unavailable"))
                    span.set_status(trace.Status(trace.StatusCode.ERROR, "Database service unavailable"))
                    raise HTTPException(status_code=503, detail="Database service unavailable")

@app.get("/api/preset/{preset_id}")
async def get_preset_data(preset_id: str, authorization: str = Header(None), request: Request = None):
    """Retrieve preset data items - requires authentication"""
    start_time = time.time()
    request_counter.add(1, {"method": "GET", "endpoint": "/api/preset/{id}"})
    
    with tracer.start_as_current_span("app.get_preset") as span:
        span.set_attribute("http.method", "GET")
        span.set_attribute("http.route", "/api/preset/{preset_id}")
        span.set_attribute("preset.id", preset_id)
        
        if not authorization:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Missing authorization"))
            raise HTTPException(status_code=401, detail="Missing authorization header")
        
        # Validate token with auth service
        with tracer.start_as_current_span("app.validate_token") as auth_span:
            auth_span.set_attribute("service", "auth-service")
            async with httpx.AsyncClient() as client:
                try:
                    auth_response = await client.post(
                        f"{AUTH_SERVICE_URL}/validate",
                        headers={"Authorization": authorization},
                        timeout=5.0
                    )
                    if auth_response.status_code != 200:
                        auth_span.set_status(trace.Status(trace.StatusCode.ERROR, "Invalid token"))
                        span.set_status(trace.Status(trace.StatusCode.ERROR, "Invalid token"))
                        raise HTTPException(status_code=401, detail="Invalid token")
                except httpx.RequestError:
                    auth_span.set_status(trace.Status(trace.StatusCode.ERROR, "Auth service unavailable"))
                    span.set_status(trace.Status(trace.StatusCode.ERROR, "Auth service unavailable"))
                    raise HTTPException(status_code=503, detail="Auth service unavailable")
        
        # Preset data mappings
        preset_data = {
            "welcome": {"message": "Welcome to the microservices application", "version": "1.0"},
            "status": {"services": ["app", "auth", "db"], "status": "operational"},
            "info": {"description": "This is a microservices demo with OpenTelemetry", "author": "CNIT48101 Team"}
        }
        
        if preset_id in preset_data:
            span.set_attribute("preset.found", True)
            duration = time.time() - start_time
            request_duration.record(duration, {"method": "GET", "endpoint": "/api/preset/{id}", "status": "200"})
            return {"preset_id": preset_id, "data": preset_data[preset_id]}
        else:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Preset not found"))
            raise HTTPException(status_code=404, detail=f"Preset '{preset_id}' not found. Available: {list(preset_data.keys())}")

@app.get("/api/presets")
async def list_presets(authorization: str = Header(None), request: Request = None):
    """List all available preset data - requires authentication"""
    start_time = time.time()
    request_counter.add(1, {"method": "GET", "endpoint": "/api/presets"})
    
    with tracer.start_as_current_span("app.list_presets") as span:
        span.set_attribute("http.method", "GET")
        span.set_attribute("http.route", "/api/presets")
        
        if not authorization:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Missing authorization"))
            raise HTTPException(status_code=401, detail="Missing authorization header")
        
        # Validate token with auth service
        with tracer.start_as_current_span("app.validate_token") as auth_span:
            auth_span.set_attribute("service", "auth-service")
            async with httpx.AsyncClient() as client:
                try:
                    auth_response = await client.post(
                        f"{AUTH_SERVICE_URL}/validate",
                        headers={"Authorization": authorization},
                        timeout=5.0
                    )
                    if auth_response.status_code != 200:
                        auth_span.set_status(trace.Status(trace.StatusCode.ERROR, "Invalid token"))
                        span.set_status(trace.Status(trace.StatusCode.ERROR, "Invalid token"))
                        raise HTTPException(status_code=401, detail="Invalid token")
                except httpx.RequestError:
                    auth_span.set_status(trace.Status(trace.StatusCode.ERROR, "Auth service unavailable"))
                    span.set_status(trace.Status(trace.StatusCode.ERROR, "Auth service unavailable"))
                    raise HTTPException(status_code=503, detail="Auth service unavailable")
        
        duration = time.time() - start_time
        request_duration.record(duration, {"method": "GET", "endpoint": "/api/presets", "status": "200"})
        return {
            "available_presets": ["welcome", "status", "info"],
            "description": "Use /api/preset/{preset_id} to retrieve specific preset data"
        }

@app.post("/api/seed")
async def seed_preset_data(authorization: str = Header(None), request: Request = None):
    """Seed database with preset data - requires authentication"""
    start_time = time.time()
    request_counter.add(1, {"method": "POST", "endpoint": "/api/seed"})
    
    with tracer.start_as_current_span("app.seed_data") as span:
        span.set_attribute("http.method", "POST")
        span.set_attribute("http.route", "/api/seed")
        
        if not authorization:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Missing authorization"))
            raise HTTPException(status_code=401, detail="Missing authorization header")
        
        # Validate token with auth service
        with tracer.start_as_current_span("app.validate_token") as auth_span:
            auth_span.set_attribute("service", "auth-service")
            async with httpx.AsyncClient() as client:
                try:
                    auth_response = await client.post(
                        f"{AUTH_SERVICE_URL}/validate",
                        headers={"Authorization": authorization},
                        timeout=5.0
                    )
                    if auth_response.status_code != 200:
                        auth_span.set_status(trace.Status(trace.StatusCode.ERROR, "Invalid token"))
                        span.set_status(trace.Status(trace.StatusCode.ERROR, "Invalid token"))
                        raise HTTPException(status_code=401, detail="Invalid token")
                except httpx.RequestError:
                    auth_span.set_status(trace.Status(trace.StatusCode.ERROR, "Auth service unavailable"))
                    span.set_status(trace.Status(trace.StatusCode.ERROR, "Auth service unavailable"))
                    raise HTTPException(status_code=503, detail="Auth service unavailable")
        
        # Seed data
        seed_items = [
            {"name": "Sample Item 1", "type": "test", "value": 100},
            {"name": "Sample Item 2", "type": "demo", "value": 200},
            {"name": "Sample Item 3", "type": "example", "value": 300}
        ]
        
        stored_ids = []
        with tracer.start_as_current_span("app.seed_items") as seed_span:
            seed_span.set_attribute("items.count", len(seed_items))
            async with httpx.AsyncClient() as client:
                for idx, item in enumerate(seed_items):
                    with tracer.start_as_current_span("app.seed_item") as item_span:
                        item_span.set_attribute("item.index", idx)
                        try:
                            db_response = await client.post(
                                f"{DB_SERVICE_URL}/store",
                                json=item,
                                headers={"Authorization": authorization},
                                timeout=5.0
                            )
                            if db_response.status_code == 200:
                                item_id = db_response.json()["id"]
                                stored_ids.append(item_id)
                                item_span.set_attribute("item.id", item_id)
                        except httpx.RequestError:
                            item_span.set_status(trace.Status(trace.StatusCode.ERROR, "Failed to store item"))
        
        span.set_attribute("items.created", len(stored_ids))
        duration = time.time() - start_time
        request_duration.record(duration, {"method": "POST", "endpoint": "/api/seed", "status": "200"})
        return {
            "status": "seeded",
            "items_created": len(stored_ids),
            "item_ids": stored_ids
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)

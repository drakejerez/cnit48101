from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse
import jwt
import os
import httpx
import time
from datetime import datetime, timedelta
from opentelemetry import trace
from otel_instrumentation import instrument_fastapi

app = FastAPI(title="Auth Service")

# Setup OpenTelemetry
tracer, meter, request_counter, request_duration = instrument_fastapi(app, "auth-service")

SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRY_MINUTES = 30
DB_SERVICE_URL = os.getenv("DB_SERVICE_URL", "http://localhost:8082")

@app.get("/")
def root():
    return {"message": "Auth Service", "status": "running"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/login")
async def login(credentials: dict, request: Request = None):
    """Generate JWT token for valid credentials"""
    start_time = time.time()
    request_counter.add(1, {"method": "POST", "endpoint": "/login"})
    
    with tracer.start_as_current_span("auth.login") as span:
        span.set_attribute("http.method", "POST")
        span.set_attribute("http.route", "/login")
        
        username = credentials.get("username")
        password = credentials.get("password")
        
        if not username or not password:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Missing credentials"))
            raise HTTPException(status_code=401, detail="Username and password required")
        
        span.set_attribute("user.username", username)
        
        # Validate credentials against database
        with tracer.start_as_current_span("auth.validate_credentials") as db_span:
            db_span.set_attribute("service", "db-service")
            async with httpx.AsyncClient() as client:
                try:
                    db_response = await client.get(
                        f"{DB_SERVICE_URL}/user/{username}",
                        timeout=5.0
                    )
                    if db_response.status_code != 200:
                        db_span.set_status(trace.Status(trace.StatusCode.ERROR, "User not found"))
                        span.set_status(trace.Status(trace.StatusCode.ERROR, "Invalid credentials"))
                        raise HTTPException(status_code=401, detail="Invalid credentials")
                    
                    user_data = db_response.json()
                    if user_data.get("password") != password:
                        db_span.set_status(trace.Status(trace.StatusCode.ERROR, "Invalid password"))
                        span.set_status(trace.Status(trace.StatusCode.ERROR, "Invalid credentials"))
                        raise HTTPException(status_code=401, detail="Invalid credentials")
                    
                    # Generate token
                    with tracer.start_as_current_span("auth.generate_token") as token_span:
                        expiration = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRY_MINUTES)
                        payload = {
                            "username": username,
                            "exp": expiration,
                            "iat": datetime.utcnow()
                        }
                        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
                        token_span.set_attribute("token.expires_in_minutes", TOKEN_EXPIRY_MINUTES)
                        span.set_attribute("auth.success", True)
                        
                        duration = time.time() - start_time
                        request_duration.record(duration, {"method": "POST", "endpoint": "/login", "status": "200"})
                        return {"token": token, "expires_in": TOKEN_EXPIRY_MINUTES * 60}
                except httpx.RequestError:
                    db_span.set_status(trace.Status(trace.StatusCode.ERROR, "Database service unavailable"))
                    span.set_status(trace.Status(trace.StatusCode.ERROR, "Database service unavailable"))
                    raise HTTPException(status_code=503, detail="Database service unavailable")

@app.post("/validate")
def validate_token(authorization: str = Header(None), request: Request = None):
    """Validate JWT token"""
    start_time = time.time()
    request_counter.add(1, {"method": "POST", "endpoint": "/validate"})
    
    with tracer.start_as_current_span("auth.validate_token") as span:
        span.set_attribute("http.method", "POST")
        span.set_attribute("http.route", "/validate")
        
        if not authorization:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Missing authorization header"))
            raise HTTPException(status_code=401, detail="Missing authorization header")
        
        # Extract token from "Bearer <token>" format
        try:
            if authorization.startswith("Bearer "):
                token = authorization.split(" ")[1]
            else:
                token = authorization
        except IndexError:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Invalid authorization format"))
            raise HTTPException(status_code=401, detail="Invalid authorization format")
        
        try:
            # Decode and validate token
            with tracer.start_as_current_span("auth.decode_token") as decode_span:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                username = payload.get("username")
                decode_span.set_attribute("user.username", username)
                span.set_attribute("user.username", username)
                span.set_attribute("auth.valid", True)
                
                duration = time.time() - start_time
                request_duration.record(duration, {"method": "POST", "endpoint": "/validate", "status": "200"})
                return {
                    "valid": True,
                    "username": username,
                    "expires_at": payload.get("exp")
                }
        except jwt.ExpiredSignatureError:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Token expired"))
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError as e:
            span.set_status(trace.Status(trace.StatusCode.ERROR, f"Invalid token: {str(e)}"))
            raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/token/info")
def token_info(authorization: str = Header(None), request: Request = None):
    """Get information about the current token"""
    start_time = time.time()
    request_counter.add(1, {"method": "GET", "endpoint": "/token/info"})
    
    with tracer.start_as_current_span("auth.token_info") as span:
        span.set_attribute("http.method", "GET")
        span.set_attribute("http.route", "/token/info")
        
        if not authorization:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Missing authorization header"))
            raise HTTPException(status_code=401, detail="Missing authorization header")
        
        try:
            if authorization.startswith("Bearer "):
                token = authorization.split(" ")[1]
            else:
                token = authorization
            
            with tracer.start_as_current_span("auth.decode_token") as decode_span:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                username = payload.get("username")
                decode_span.set_attribute("user.username", username)
                span.set_attribute("user.username", username)
                
                duration = time.time() - start_time
                request_duration.record(duration, {"method": "GET", "endpoint": "/token/info", "status": "200"})
                return {
                    "username": username,
                    "issued_at": payload.get("iat"),
                    "expires_at": payload.get("exp")
                }
        except jwt.ExpiredSignatureError:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Token expired"))
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError as e:
            span.set_status(trace.Status(trace.StatusCode.ERROR, f"Invalid token: {str(e)}"))
            raise HTTPException(status_code=401, detail="Invalid token")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)

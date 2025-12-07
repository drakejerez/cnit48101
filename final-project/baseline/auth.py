from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse
import jwt
import os
import httpx
from datetime import datetime, timedelta

app = FastAPI(title="Auth Service")

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
async def login(credentials: dict):
    """Generate JWT token for valid credentials"""
    username = credentials.get("username")
    password = credentials.get("password")
    
    if not username or not password:
        raise HTTPException(status_code=401, detail="Username and password required")
    
    # Validate credentials against database
    async with httpx.AsyncClient() as client:
        try:
            db_response = await client.get(
                f"{DB_SERVICE_URL}/user/{username}",
                timeout=5.0
            )
            if db_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid credentials")
            
            user_data = db_response.json()
            if user_data.get("password") != password:
                raise HTTPException(status_code=401, detail="Invalid credentials")
            
            # Generate token
            expiration = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRY_MINUTES)
            payload = {
                "username": username,
                "exp": expiration,
                "iat": datetime.utcnow()
            }
            token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
            return {"token": token, "expires_in": TOKEN_EXPIRY_MINUTES * 60}
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Database service unavailable")

@app.post("/validate")
def validate_token(authorization: str = Header(None)):
    """Validate JWT token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    # Extract token from "Bearer <token>" format
    try:
        if authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]
        else:
            token = authorization
    except IndexError:
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    try:
        # Decode and validate token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {
            "valid": True,
            "username": payload.get("username"),
            "expires_at": payload.get("exp")
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/token/info")
def token_info(authorization: str = Header(None)):
    """Get information about the current token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    try:
        if authorization.startswith("Bearer "):
            token = authorization.split(" ")[1]
        else:
            token = authorization
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {
            "username": payload.get("username"),
            "issued_at": payload.get("iat"),
            "expires_at": payload.get("exp")
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)



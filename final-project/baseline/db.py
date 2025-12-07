from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse
import sqlite3
import os
import time
import uuid
import json
from datetime import datetime

app = FastAPI(title="Database Service")

DB_PATH = os.getenv("DB_PATH", "./data/app.db")
ARTIFICIAL_LATENCY_MS = int(os.getenv("ARTIFICIAL_LATENCY_MS", "100"))

def get_db_connection():
    """Get SQLite database connection"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database schema"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Items table for application data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id TEXT PRIMARY KEY,
            data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Users table for authentication
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert default users if they don't exist
    default_users = [
        ("admin", "admin123"),
        ("user1", "password1"),
        ("testuser", "testpass")
    ]
    for username, password in default_users:
        cursor.execute("""
            INSERT OR IGNORE INTO users (username, password)
            VALUES (?, ?)
        """, (username, password))
    
    conn.commit()
    conn.close()

@app.on_event("startup")
def startup():
    init_db()

@app.get("/")
def root():
    return {"message": "Database Service", "status": "running"}

@app.get("/health")
def health():
    return {"status": "healthy"}

def inject_latency():
    """Inject artificial latency to simulate database operations"""
    if ARTIFICIAL_LATENCY_MS > 0:
        time.sleep(ARTIFICIAL_LATENCY_MS / 1000.0)

@app.post("/store")
def store_data(data: dict, authorization: str = Header(None)):
    """Store data in database"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    inject_latency()
    
    item_id = str(uuid.uuid4())
    data_json = json.dumps(data)
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO items (id, data, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """, (item_id, data_json, datetime.utcnow(), datetime.utcnow()))
        conn.commit()
        
        return {
            "id": item_id,
            "status": "stored",
            "created_at": datetime.utcnow().isoformat()
        }
    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()

@app.get("/retrieve/{item_id}")
def retrieve_data(item_id: str, authorization: str = Header(None)):
    """Retrieve data from database"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    inject_latency()
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, data, created_at, updated_at FROM items WHERE id = ?", (item_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Item not found")
        
        # Parse JSON data
        try:
            data = json.loads(row["data"])
        except json.JSONDecodeError:
            data = row["data"]
        
        return {
            "id": row["id"],
            "data": data,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"]
        }
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()

@app.get("/list")
def list_items(authorization: str = Header(None), limit: int = 10):
    """List all items in database"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    inject_latency()
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, data, created_at, updated_at FROM items ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        
        items = []
        for row in rows:
            # Parse JSON data
            try:
                data = json.loads(row["data"])
            except json.JSONDecodeError:
                data = row["data"]
            
            items.append({
                "id": row["id"],
                "data": data,
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            })
        
        return {"items": items, "count": len(items)}
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()

@app.delete("/delete/{item_id}")
def delete_data(item_id: str, authorization: str = Header(None)):
    """Delete data from database"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    inject_latency()
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Item not found")
        
        return {"id": item_id, "status": "deleted"}
    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()

@app.get("/user/{username}")
def get_user(username: str):
    """Get user by username (for auth service)"""
    inject_latency()
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT username, password FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "username": row["username"],
            "password": row["password"]
        }
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()

@app.post("/user")
def create_user(user_data: dict):
    """Create a new user (for auth service)"""
    inject_latency()
    
    username = user_data.get("username")
    password = user_data.get("password")
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (username, password)
            VALUES (?, ?)
        """, (username, password))
        conn.commit()
        
        return {
            "username": username,
            "status": "created",
            "created_at": datetime.utcnow().isoformat()
        }
    except sqlite3.IntegrityError:
        conn.rollback()
        raise HTTPException(status_code=409, detail="User already exists")
    except sqlite3.Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)



from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse
import sqlite3
import os
import time
import uuid
import json
from datetime import datetime
from opentelemetry import trace
from otel_instrumentation import instrument_fastapi

app = FastAPI(title="Database Service")

# Setup OpenTelemetry
tracer, meter, request_counter, request_duration = instrument_fastapi(app, "db-service")

DB_PATH = os.getenv("DB_PATH", "./data/app.db")
ARTIFICIAL_LATENCY_MS = int(os.getenv("ARTIFICIAL_LATENCY_MS", "100"))

# Database metrics
db_operations_counter = meter.create_counter(
    name="db_operations_total",
    description="Total number of database operations",
    unit="1"
)

db_operation_duration = meter.create_histogram(
    name="db_operation_duration_seconds",
    description="Database operation duration in seconds",
    unit="s"
)

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
def store_data(data: dict, authorization: str = Header(None), request: Request = None):
    """Store data in database"""
    start_time = time.time()
    request_counter.add(1, {"method": "POST", "endpoint": "/store"})
    db_operations_counter.add(1, {"operation": "insert", "table": "items"})
    
    with tracer.start_as_current_span("db.store_data") as span:
        span.set_attribute("http.method", "POST")
        span.set_attribute("http.route", "/store")
        span.set_attribute("db.operation", "insert")
        span.set_attribute("db.table", "items")
        
        if not authorization:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Missing authorization"))
            raise HTTPException(status_code=401, detail="Missing authorization header")
        
        inject_latency()
        
        item_id = str(uuid.uuid4())
        data_json = json.dumps(data)
        span.set_attribute("item.id", item_id)
        
        conn = get_db_connection()
        try:
            with tracer.start_as_current_span("db.execute_insert") as db_span:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO items (id, data, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (item_id, data_json, datetime.utcnow(), datetime.utcnow()))
                conn.commit()
                db_span.set_attribute("db.rows_affected", 1)
            
            duration = time.time() - start_time
            db_operation_duration.record(duration, {"operation": "insert", "table": "items"})
            request_duration.record(duration, {"method": "POST", "endpoint": "/store", "status": "200"})
            
            return {
                "id": item_id,
                "status": "stored",
                "created_at": datetime.utcnow().isoformat()
            }
        except sqlite3.Error as e:
            conn.rollback()
            span.set_status(trace.Status(trace.StatusCode.ERROR, f"Database error: {str(e)}"))
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        finally:
            conn.close()

@app.get("/retrieve/{item_id}")
def retrieve_data(item_id: str, authorization: str = Header(None), request: Request = None):
    """Retrieve data from database"""
    start_time = time.time()
    request_counter.add(1, {"method": "GET", "endpoint": "/retrieve/{id}"})
    db_operations_counter.add(1, {"operation": "select", "table": "items"})
    
    with tracer.start_as_current_span("db.retrieve_data") as span:
        span.set_attribute("http.method", "GET")
        span.set_attribute("http.route", "/retrieve/{item_id}")
        span.set_attribute("db.operation", "select")
        span.set_attribute("db.table", "items")
        span.set_attribute("item.id", item_id)
        
        if not authorization:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Missing authorization"))
            raise HTTPException(status_code=401, detail="Missing authorization header")
        
        inject_latency()
        
        conn = get_db_connection()
        try:
            with tracer.start_as_current_span("db.execute_select") as db_span:
                cursor = conn.cursor()
                cursor.execute("SELECT id, data, created_at, updated_at FROM items WHERE id = ?", (item_id,))
                row = cursor.fetchone()
                db_span.set_attribute("db.rows_returned", 1 if row else 0)
            
            if not row:
                span.set_status(trace.Status(trace.StatusCode.ERROR, "Item not found"))
                raise HTTPException(status_code=404, detail="Item not found")
            
            # Parse JSON data
            try:
                data = json.loads(row["data"])
            except json.JSONDecodeError:
                data = row["data"]
            
            duration = time.time() - start_time
            db_operation_duration.record(duration, {"operation": "select", "table": "items"})
            request_duration.record(duration, {"method": "GET", "endpoint": "/retrieve/{id}", "status": "200"})
            
            return {
                "id": row["id"],
                "data": data,
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }
        except sqlite3.Error as e:
            span.set_status(trace.Status(trace.StatusCode.ERROR, f"Database error: {str(e)}"))
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        finally:
            conn.close()

@app.get("/list")
def list_items(authorization: str = Header(None), limit: int = 10, request: Request = None):
    """List all items in database"""
    start_time = time.time()
    request_counter.add(1, {"method": "GET", "endpoint": "/list"})
    db_operations_counter.add(1, {"operation": "select", "table": "items"})
    
    with tracer.start_as_current_span("db.list_items") as span:
        span.set_attribute("http.method", "GET")
        span.set_attribute("http.route", "/list")
        span.set_attribute("db.operation", "select")
        span.set_attribute("db.table", "items")
        span.set_attribute("db.limit", limit)
        
        if not authorization:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Missing authorization"))
            raise HTTPException(status_code=401, detail="Missing authorization header")
        
        inject_latency()
        
        conn = get_db_connection()
        try:
            with tracer.start_as_current_span("db.execute_select") as db_span:
                cursor = conn.cursor()
                cursor.execute("SELECT id, data, created_at, updated_at FROM items ORDER BY created_at DESC LIMIT ?", (limit,))
                rows = cursor.fetchall()
                db_span.set_attribute("db.rows_returned", len(rows))
            
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
            
            span.set_attribute("items.count", len(items))
            duration = time.time() - start_time
            db_operation_duration.record(duration, {"operation": "select", "table": "items"})
            request_duration.record(duration, {"method": "GET", "endpoint": "/list", "status": "200"})
            
            return {"items": items, "count": len(items)}
        except sqlite3.Error as e:
            span.set_status(trace.Status(trace.StatusCode.ERROR, f"Database error: {str(e)}"))
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        finally:
            conn.close()

@app.delete("/delete/{item_id}")
def delete_data(item_id: str, authorization: str = Header(None), request: Request = None):
    """Delete data from database"""
    start_time = time.time()
    request_counter.add(1, {"method": "DELETE", "endpoint": "/delete/{id}"})
    db_operations_counter.add(1, {"operation": "delete", "table": "items"})
    
    with tracer.start_as_current_span("db.delete_data") as span:
        span.set_attribute("http.method", "DELETE")
        span.set_attribute("http.route", "/delete/{item_id}")
        span.set_attribute("db.operation", "delete")
        span.set_attribute("db.table", "items")
        span.set_attribute("item.id", item_id)
        
        if not authorization:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Missing authorization"))
            raise HTTPException(status_code=401, detail="Missing authorization header")
        
        inject_latency()
        
        conn = get_db_connection()
        try:
            with tracer.start_as_current_span("db.execute_delete") as db_span:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM items WHERE id = ?", (item_id,))
                conn.commit()
                db_span.set_attribute("db.rows_affected", cursor.rowcount)
            
            if cursor.rowcount == 0:
                span.set_status(trace.Status(trace.StatusCode.ERROR, "Item not found"))
                raise HTTPException(status_code=404, detail="Item not found")
            
            duration = time.time() - start_time
            db_operation_duration.record(duration, {"operation": "delete", "table": "items"})
            request_duration.record(duration, {"method": "DELETE", "endpoint": "/delete/{id}", "status": "200"})
            
            return {"id": item_id, "status": "deleted"}
        except sqlite3.Error as e:
            conn.rollback()
            span.set_status(trace.Status(trace.StatusCode.ERROR, f"Database error: {str(e)}"))
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        finally:
            conn.close()

@app.get("/user/{username}")
def get_user(username: str, request: Request = None):
    """Get user by username (for auth service)"""
    start_time = time.time()
    request_counter.add(1, {"method": "GET", "endpoint": "/user/{username}"})
    db_operations_counter.add(1, {"operation": "select", "table": "users"})
    
    with tracer.start_as_current_span("db.get_user") as span:
        span.set_attribute("http.method", "GET")
        span.set_attribute("http.route", "/user/{username}")
        span.set_attribute("db.operation", "select")
        span.set_attribute("db.table", "users")
        span.set_attribute("user.username", username)
        
        inject_latency()
        
        conn = get_db_connection()
        try:
            with tracer.start_as_current_span("db.execute_select") as db_span:
                cursor = conn.cursor()
                cursor.execute("SELECT username, password FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()
                db_span.set_attribute("db.rows_returned", 1 if row else 0)
            
            if not row:
                span.set_status(trace.Status(trace.StatusCode.ERROR, "User not found"))
                raise HTTPException(status_code=404, detail="User not found")
            
            duration = time.time() - start_time
            db_operation_duration.record(duration, {"operation": "select", "table": "users"})
            request_duration.record(duration, {"method": "GET", "endpoint": "/user/{username}", "status": "200"})
            
            return {
                "username": row["username"],
                "password": row["password"]
            }
        except sqlite3.Error as e:
            span.set_status(trace.Status(trace.StatusCode.ERROR, f"Database error: {str(e)}"))
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        finally:
            conn.close()

@app.post("/user")
def create_user(user_data: dict, request: Request = None):
    """Create a new user (for auth service)"""
    start_time = time.time()
    request_counter.add(1, {"method": "POST", "endpoint": "/user"})
    db_operations_counter.add(1, {"operation": "insert", "table": "users"})
    
    with tracer.start_as_current_span("db.create_user") as span:
        span.set_attribute("http.method", "POST")
        span.set_attribute("http.route", "/user")
        span.set_attribute("db.operation", "insert")
        span.set_attribute("db.table", "users")
        
        inject_latency()
        
        username = user_data.get("username")
        password = user_data.get("password")
        
        if not username or not password:
            span.set_status(trace.Status(trace.StatusCode.ERROR, "Missing username or password"))
            raise HTTPException(status_code=400, detail="Username and password required")
        
        span.set_attribute("user.username", username)
        
        conn = get_db_connection()
        try:
            with tracer.start_as_current_span("db.execute_insert") as db_span:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (username, password)
                    VALUES (?, ?)
                """, (username, password))
                conn.commit()
                db_span.set_attribute("db.rows_affected", 1)
            
            duration = time.time() - start_time
            db_operation_duration.record(duration, {"operation": "insert", "table": "users"})
            request_duration.record(duration, {"method": "POST", "endpoint": "/user", "status": "200"})
            
            return {
                "username": username,
                "status": "created",
                "created_at": datetime.utcnow().isoformat()
            }
        except sqlite3.IntegrityError:
            conn.rollback()
            span.set_status(trace.Status(trace.StatusCode.ERROR, "User already exists"))
            raise HTTPException(status_code=409, detail="User already exists")
        except sqlite3.Error as e:
            conn.rollback()
            span.set_status(trace.Status(trace.StatusCode.ERROR, f"Database error: {str(e)}"))
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        finally:
            conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)

#!/usr/bin/env python3
"""Traffic generator for microservices testing"""
import requests
import time
import random
import threading
import argparse
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

class TrafficGenerator:
    def __init__(self, base_url, auth_url, num_threads=10, duration=60, rate=10):
        self.base_url = base_url
        self.auth_url = auth_url
        self.num_threads = num_threads
        self.duration = duration
        self.rate = rate  # requests per second per thread
        self.token = None
        self.stats = {
            "total_requests": 0,
            "successful": 0,
            "failed": 0,
            "errors": 0,
            "latencies": [],
            "start_time": None,
            "end_time": None
        }
        self.lock = threading.Lock()
        
    def login(self):
        """Get authentication token"""
        try:
            response = requests.post(
                f"{self.auth_url}/login",
                json={"username": "admin", "password": "admin123"},
                timeout=5
            )
            if response.status_code == 200:
                self.token = response.json().get("token")
                print(f"✅ Authenticated successfully")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    def make_request(self, endpoint, method="GET", data=None):
        """Make a single request"""
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        url = f"{self.base_url}{endpoint}"
        
        start = time.time()
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=10)
            else:
                return False, 0, "Invalid method"
            
            latency = time.time() - start
            success = 200 <= response.status_code < 300
            
            with self.lock:
                self.stats["total_requests"] += 1
                if success:
                    self.stats["successful"] += 1
                else:
                    self.stats["failed"] += 1
                self.stats["latencies"].append(latency)
            
            return success, latency, response.status_code
        except Exception as e:
            latency = time.time() - start
            with self.lock:
                self.stats["total_requests"] += 1
                self.stats["errors"] += 1
                self.stats["latencies"].append(latency)
            return False, latency, str(e)
    
    def worker(self, worker_id):
        """Worker thread that generates traffic"""
        endpoints = [
            ("/api/presets", "GET", None),
            ("/api/preset/welcome", "GET", None),
            ("/api/preset/status", "GET", None),
            ("/api/preset/info", "GET", None),
            ("/api/data", "POST", {"test": f"worker-{worker_id}", "value": random.randint(1, 1000)}),
        ]
        
        end_time = time.time() + self.duration
        request_interval = 1.0 / self.rate
        
        while time.time() < end_time:
            endpoint_info = random.choice(endpoints)
            endpoint = endpoint_info[0]
            method = endpoint_info[1]
            data = endpoint_info[2] if len(endpoint_info) > 2 else None
            
            success, latency, status = self.make_request(endpoint, method, data)
            
            if worker_id == 0 and self.stats["total_requests"] % 100 == 0:
                print(f"  Worker {worker_id}: {method} {endpoint} - {status} ({latency*1000:.2f}ms)")
            
            time.sleep(request_interval)
    
    def spike_worker(self, spike_duration=10, spike_rate=50):
        """Generate traffic spike"""
        print(f"\n🔥 Generating traffic spike: {spike_rate} req/s for {spike_duration}s")
        endpoints = [
            ("/api/presets", "GET", None),
            ("/api/preset/welcome", "GET", None),
            ("/api/data", "POST", {"spike": True, "value": random.randint(1, 1000)}),
        ]
        
        end_time = time.time() + spike_duration
        request_interval = 1.0 / spike_rate
        
        while time.time() < end_time:
            endpoint_info = random.choice(endpoints)
            endpoint = endpoint_info[0]
            method = endpoint_info[1]
            data = endpoint_info[2] if len(endpoint_info) > 2 else None
            self.make_request(endpoint, method, data)
            time.sleep(request_interval)
    
    def error_worker(self, error_rate=0.1):
        """Generate requests that will fail (for error testing)"""
        print(f"\n⚠️  Generating error requests ({error_rate*100}% error rate)")
        endpoints = [
            ("/api/data/invalid-id", "GET", None),  # Will 404
            ("/api/preset/invalid", "GET", None),    # Will 404
        ]
        
        for _ in range(int(self.stats["total_requests"] * error_rate)):
            endpoint_info = random.choice(endpoints)
            endpoint = endpoint_info[0]
            method = endpoint_info[1]
            data = endpoint_info[2] if len(endpoint_info) > 2 else None
            self.make_request(endpoint, method, data)
    
    def run(self):
        """Run traffic generation"""
        if not self.login():
            return
        
        print(f"\n🚀 Starting traffic generation:")
        print(f"   Threads: {self.num_threads}")
        print(f"   Duration: {self.duration}s")
        print(f"   Rate: {self.rate} req/s per thread")
        print(f"   Total expected: ~{self.num_threads * self.rate * self.duration} requests\n")
        
        self.stats["start_time"] = datetime.now()
        
        # Normal traffic
        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            futures = [executor.submit(self.worker, i) for i in range(self.num_threads)]
            
            # Generate spike halfway through
            if self.duration > 20:
                time.sleep(self.duration / 2)
                executor.submit(self.spike_worker, spike_duration=10, spike_rate=self.rate * 5)
            
            # Wait for all workers
            for future in as_completed(futures):
                future.result()
        
        # Generate some error requests
        self.error_worker(error_rate=0.05)
        
        self.stats["end_time"] = datetime.now()
        self.print_stats()
    
    def print_stats(self):
        """Print statistics"""
        duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()
        latencies = self.stats["latencies"]
        
        print("\n" + "="*60)
        print("TRAFFIC GENERATION STATISTICS")
        print("="*60)
        print(f"Duration: {duration:.2f}s")
        print(f"Total Requests: {self.stats['total_requests']}")
        print(f"Successful: {self.stats['successful']} ({self.stats['successful']/max(self.stats['total_requests'],1)*100:.1f}%)")
        print(f"Failed: {self.stats['failed']} ({self.stats['failed']/max(self.stats['total_requests'],1)*100:.1f}%)")
        print(f"Errors: {self.stats['errors']} ({self.stats['errors']/max(self.stats['total_requests'],1)*100:.1f}%)")
        
        if latencies:
            print(f"\nLatency Statistics:")
            print(f"  Min: {min(latencies)*1000:.2f}ms")
            print(f"  Max: {max(latencies)*1000:.2f}ms")
            print(f"  Avg: {sum(latencies)/len(latencies)*1000:.2f}ms")
            print(f"  P50: {sorted(latencies)[len(latencies)//2]*1000:.2f}ms")
            print(f"  P95: {sorted(latencies)[int(len(latencies)*0.95)]*1000:.2f}ms")
            print(f"  P99: {sorted(latencies)[int(len(latencies)*0.99)]*1000:.2f}ms")
        
        print(f"\nThroughput: {self.stats['total_requests']/duration:.2f} req/s")
        print("="*60)

def main():
    parser = argparse.ArgumentParser(description="Traffic generator for microservices")
    parser.add_argument("--app-url", default="http://localhost:8080", help="App service URL")
    parser.add_argument("--auth-url", default="http://localhost:8081", help="Auth service URL")
    parser.add_argument("--threads", type=int, default=10, help="Number of worker threads")
    parser.add_argument("--duration", type=int, default=60, help="Duration in seconds")
    parser.add_argument("--rate", type=int, default=10, help="Requests per second per thread")
    
    args = parser.parse_args()
    
    generator = TrafficGenerator(
        base_url=args.app_url,
        auth_url=args.auth_url,
        num_threads=args.threads,
        duration=args.duration,
        rate=args.rate
    )
    
    generator.run()

if __name__ == "__main__":
    main()


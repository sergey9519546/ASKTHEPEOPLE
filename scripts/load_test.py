#!/usr/bin/env python3
"""
Load Testing Script for ASKTHEPEOPLE API

Tests concurrent upload handling, response times, and system stability.
Requires the backend to be running on http://localhost:5000

Usage:
    python scripts/load_test.py              # Run default test (10 concurrent users)
    python scripts/load_test.py -u 50        # Run with 50 concurrent users
    python scripts/load_test.py -d 60        # Run for 60 seconds
    python scripts/load_test.py --stress     # Run stress test (100 users, 120s)

Requirements:
    pip install requests tqdm
"""

import argparse
import json
import time
import threading
import statistics
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field

try:
    import requests
    from tqdm import tqdm
except ImportError:
    print("ERROR: Missing dependencies. Install with: pip install requests tqdm")
    exit(1)


@dataclass
class TestResult:
    """Stores results for a single request"""
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    success: bool
    error_message: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class TestSummary:
    """Aggregated test results"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time_ms: float = 0.0
    min_response_time_ms: float = 0.0
    max_response_time_ms: float = 0.0
    p95_response_time_ms: float = 0.0
    p99_response_time_ms: float = 0.0
    requests_per_second: float = 0.0
    errors: List[str] = field(default_factory=list)


class LoadTester:
    """Concurrent load testing engine"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url.rstrip('/')
        self.results: List[TestResult] = []
        self.results_lock = threading.Lock()
        self.stop_flag = threading.Event()
        
    def _make_request(self, method: str, endpoint: str, **kwargs) -> TestResult:
        """Execute a single HTTP request and record metrics"""
        url = f"{self.base_url}{endpoint}"
        start_time = time.time()
        
        try:
            response = requests.request(method, url, timeout=30, **kwargs)
            elapsed_ms = (time.time() - start_time) * 1000
            
            return TestResult(
                endpoint=endpoint,
                method=method,
                status_code=response.status_code,
                response_time_ms=elapsed_ms,
                success=200 <= response.status_code < 400,
                error_message=None if response.ok else f"HTTP {response.status_code}"
            )
        except requests.exceptions.RequestException as e:
            elapsed_ms = (time.time() - start_time) * 1000
            return TestResult(
                endpoint=endpoint,
                method=method,
                status_code=0,
                response_time_ms=elapsed_ms,
                success=False,
                error_message=str(e)
            )
    
    def _worker(self, worker_id: int, test_sequence: List[Dict], 
                iterations: int, pbar: Optional[tqdm] = None):
        """Worker thread that executes test sequences"""
        for i in range(iterations):
            if self.stop_flag.is_set():
                break
                
            for req in test_sequence:
                if self.stop_flag.is_set():
                    break
                    
                result = self._make_request(**req)
                
                with self.results_lock:
                    self.results.append(result)
                
                if pbar:
                    pbar.update(1)
    
    def run_test(self, concurrent_users: int, duration_seconds: int, 
                 test_sequence: List[Dict]) -> TestSummary:
        """
        Run load test with specified concurrency and duration
        
        Args:
            concurrent_users: Number of parallel threads
            duration_seconds: How long to run the test
            test_sequence: List of request dicts with keys: method, endpoint, [data], [headers]
        
        Returns:
            TestSummary with aggregated metrics
        """
        print(f"\n🚀 Starting load test:")
        print(f"   Base URL: {self.base_url}")
        print(f"   Concurrent Users: {concurrent_users}")
        print(f"   Duration: {duration_seconds}s")
        print(f"   Endpoints: {[r['endpoint'] for r in test_sequence]}")
        print(f"   Start Time: {datetime.now().isoformat()}")
        print("-" * 60)
        
        self.results = []
        self.stop_flag.clear()
        
        # Calculate iterations per worker
        # Estimate: assume avg 200ms per request in sequence
        avg_request_time = 0.2
        sequence_time = len(test_sequence) * avg_request_time
        iterations_per_worker = max(1, int(duration_seconds / sequence_time))
        
        total_expected_requests = concurrent_users * iterations_per_worker * len(test_sequence)
        
        threads = []
        pbar = tqdm(total=total_expected_requests, desc="Running tests", unit="req")
        
        start_time = time.time()
        
        # Spawn worker threads
        for i in range(concurrent_users):
            t = threading.Thread(
                target=self._worker,
                args=(i, test_sequence, iterations_per_worker, pbar),
                daemon=True
            )
            t.start()
            threads.append(t)
        
        # Wait for duration or completion
        time.sleep(duration_seconds)
        self.stop_flag.set()
        
        # Wait for threads to finish
        for t in threads:
            t.join(timeout=5)
        
        pbar.close()
        actual_duration = time.time() - start_time
        
        return self._calculate_summary(actual_duration)
    
    def _calculate_summary(self, duration: float) -> TestSummary:
        """Calculate aggregated metrics from results"""
        if not self.results:
            return TestSummary(errors=["No results collected"])
        
        response_times = [r.response_time_ms for r in self.results]
        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]
        
        summary = TestSummary(
            total_requests=len(self.results),
            successful_requests=len(successful),
            failed_requests=len(failed),
            avg_response_time_ms=statistics.mean(response_times),
            min_response_time_ms=min(response_times),
            max_response_time_ms=max(response_times),
            p95_response_time_ms=statistics.quantiles(response_times, n=100)[94] if len(response_times) > 1 else response_times[0],
            p99_response_time_ms=statistics.quantiles(response_times, n=100)[98] if len(response_times) > 1 else response_times[0],
            requests_per_second=len(self.results) / duration if duration > 0 else 0,
            errors=[f"{r.endpoint}: {r.error_message}" for r in failed[:10]]  # First 10 errors
        )
        
        return summary
    
    def check_health(self) -> bool:
        """Check if backend is healthy"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False


def create_test_scenarios(args) -> List[List[Dict]]:
    """Create test scenarios based on arguments"""
    scenarios = []
    
    # Scenario 1: Health Check (light load baseline)
    health_scenario = [
        {"method": "GET", "endpoint": "/health"}
    ]
    scenarios.append(("Health Check Baseline", health_scenario))
    
    # Scenario 2: API Discovery
    api_scenario = [
        {"method": "GET", "endpoint": "/api/v1/projects"},
        {"method": "GET", "endpoint": "/api/v1/simulations"}
    ]
    scenarios.append(("API Discovery", api_scenario))
    
    # Scenario 3: Full Workflow (if auth available)
    workflow_scenario = [
        {"method": "GET", "endpoint": "/health"},
        {"method": "GET", "endpoint": "/api/v1/config"},
    ]
    
    if args.token:
        headers = {"Authorization": f"Bearer {args.token}"}
        workflow_scenario.extend([
            {"method": "POST", "endpoint": "/api/v1/projects", 
             "json": {"name": f"load-test-{int(time.time())}", "description": "Auto-generated"},
             "headers": headers},
            {"method": "GET", "endpoint": "/api/v1/projects", "headers": headers}
        ])
    
    scenarios.append(("Full Workflow", workflow_scenario))
    
    return scenarios


def print_summary(scenario_name: str, summary: TestSummary):
    """Pretty print test summary"""
    print("\n" + "=" * 60)
    print(f"📊 RESULTS: {scenario_name}")
    print("=" * 60)
    
    status_color = "✅" if summary.failed_requests == 0 else "❌"
    print(f"{status_color} Total Requests:     {summary.total_requests}")
    print(f"✅ Successful:        {summary.successful_requests} ({summary.successful_requests/summary.total_requests*100:.1f}%)" if summary.total_requests > 0 else "")
    print(f"❌ Failed:            {summary.failed_requests}" if summary.failed_requests > 0 else "")
    print(f"⚡ Throughput:        {summary.requests_per_second:.2f} req/s")
    print(f"⏱️  Avg Response:     {summary.avg_response_time_ms:.2f} ms")
    print(f"⏱️  Min Response:     {summary.min_response_time_ms:.2f} ms")
    print(f"⏱️  Max Response:     {summary.max_response_time_ms:.2f} ms")
    print(f"⏱️  P95 Response:     {summary.p95_response_time_ms:.2f} ms")
    print(f"⏱️  P99 Response:     {summary.p99_response_time_ms:.2f} ms")
    
    if summary.errors:
        print(f"\n⚠️  ERRORS (first 10):")
        for error in summary.errors:
            print(f"   - {error}")
    
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Load test ASKTHEPEOPLE API")
    parser.add_argument("-u", "--users", type=int, default=10, 
                        help="Number of concurrent users (default: 10)")
    parser.add_argument("-d", "--duration", type=int, default=30,
                        help="Test duration in seconds (default: 30)")
    parser.add_argument("--stress", action="store_true",
                        help="Run stress test (100 users, 120s)")
    parser.add_argument("--token", type=str, default=None,
                        help="Auth token for protected endpoints")
    parser.add_argument("--url", type=str, default="http://localhost:5000",
                        help="Base URL of the API")
    
    args = parser.parse_args()
    
    if args.stress:
        args.users = 100
        args.duration = 120
        print("🔥 STRESS TEST MODE: 100 concurrent users, 120 seconds")
    
    tester = LoadTester(args.url)
    
    # Health check
    print("🔍 Checking backend health...")
    if not tester.check_health():
        print(f"❌ Backend at {args.url} is not responding!")
        print("   Make sure to start the server: cd backend && flask run")
        exit(1)
    print("✅ Backend is healthy\n")
    
    # Run scenarios
    scenarios = create_test_scenarios(args)
    
    all_passed = True
    
    for scenario_name, sequence in scenarios:
        summary = tester.run_test(
            concurrent_users=args.users,
            duration_seconds=args.duration,
            test_sequence=sequence
        )
        print_summary(scenario_name, summary)
        
        if summary.failed_requests > 0:
            all_passed = False
    
    # Final verdict
    print("\n" + "🏁" * 30)
    if all_passed:
        print("✅ ALL TESTS PASSED - System is ready for load!")
    else:
        print("⚠️  SOME TESTS FAILED - Review errors above")
    print("🏁" * 30)
    
    exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()

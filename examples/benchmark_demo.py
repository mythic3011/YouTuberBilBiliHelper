#!/usr/bin/env python3
"""
Simple API Performance Benchmark
Uses only built-in Python libraries to test the current FastAPI performance.
"""

import urllib.request
import urllib.error
import time
import json
import statistics
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any


class SimpleBenchmark:
    """Simple benchmark utility using built-in libraries"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.timeout = 30
    
    def make_request(self, endpoint: str) -> Dict[str, Any]:
        """Make a single HTTP request and measure performance"""
        start_time = time.time()
        
        try:
            with urllib.request.urlopen(
                f"{self.base_url}{endpoint}", 
                timeout=self.timeout
            ) as response:
                content = response.read()
                latency = (time.time() - start_time) * 1000  # Convert to ms
                
                return {
                    "success": True,
                    "status_code": response.getcode(),
                    "latency_ms": latency,
                    "response_size": len(content)
                }
        except urllib.error.HTTPError as e:
            latency = (time.time() - start_time) * 1000
            return {
                "success": False,
                "status_code": e.code,
                "latency_ms": latency,
                "error": str(e)
            }
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            return {
                "success": False,
                "status_code": 0,
                "latency_ms": latency,
                "error": str(e)
            }
    
    def run_concurrent_benchmark(
        self, 
        endpoint: str, 
        concurrent_requests: int = 10, 
        total_requests: int = 100
    ) -> Dict[str, Any]:
        """Run benchmark with concurrent requests using ThreadPoolExecutor"""
        
        print(f"🚀 Benchmarking: {endpoint}")
        print(f"   Concurrent threads: {concurrent_requests}")
        print(f"   Total requests: {total_requests}")
        
        results = []
        start_time = time.time()
        
        # Use ThreadPoolExecutor for concurrent requests
        with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
            # Submit all requests
            futures = [
                executor.submit(self.make_request, endpoint) 
                for _ in range(total_requests)
            ]
            
            # Collect results as they complete
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append({
                        "success": False,
                        "status_code": 0,
                        "latency_ms": 0,
                        "error": str(e)
                    })
        
        total_time = time.time() - start_time
        
        # Process results
        successful_results = [r for r in results if r.get("success")]
        failed_results = [r for r in results if not r.get("success")]
        
        if successful_results:
            latencies = [r["latency_ms"] for r in successful_results]
            response_sizes = [r["response_size"] for r in successful_results]
            
            # Calculate percentiles manually
            sorted_latencies = sorted(latencies)
            n = len(sorted_latencies)
            p95_index = int(0.95 * n)
            p99_index = int(0.99 * n)
            
            benchmark_results = {
                "endpoint": endpoint,
                "total_requests": total_requests,
                "successful_requests": len(successful_results),
                "failed_requests": len(failed_results),
                "success_rate_percent": (len(successful_results) / total_requests) * 100,
                "total_time_seconds": round(total_time, 3),
                "requests_per_second": round(total_requests / total_time, 2),
                "latency_stats": {
                    "min_ms": round(min(latencies), 2),
                    "max_ms": round(max(latencies), 2),
                    "mean_ms": round(statistics.mean(latencies), 2),
                    "median_ms": round(statistics.median(latencies), 2),
                    "p95_ms": round(sorted_latencies[min(p95_index, n-1)], 2),
                    "p99_ms": round(sorted_latencies[min(p99_index, n-1)], 2)
                },
                "response_size_stats": {
                    "min_bytes": min(response_sizes) if response_sizes else 0,
                    "max_bytes": max(response_sizes) if response_sizes else 0,
                    "mean_bytes": round(statistics.mean(response_sizes), 2) if response_sizes else 0
                }
            }
        else:
            benchmark_results = {
                "endpoint": endpoint,
                "total_requests": total_requests,
                "successful_requests": 0,
                "failed_requests": len(failed_results),
                "success_rate_percent": 0,
                "total_time_seconds": round(total_time, 3),
                "requests_per_second": 0,
                "error": "All requests failed",
                "sample_errors": [r.get("error", "Unknown") for r in failed_results[:3]]
            }
        
        return benchmark_results
    
    def comprehensive_benchmark(self) -> Dict[str, Any]:
        """Run comprehensive benchmark across multiple endpoints"""
        
        print("🔥 Starting Simple API Performance Benchmark")
        print("=" * 60)
        
        # Test different endpoints with varying loads
        test_cases = [
            {
                "name": "Root Endpoint",
                "endpoint": "/",
                "concurrent": 10,
                "total": 50
            },
            {
                "name": "Health Check",
                "endpoint": "/api/v2/system/health",
                "concurrent": 20,
                "total": 100
            },
            {
                "name": "Auth Status",
                "endpoint": "/api/v2/auth/status",
                "concurrent": 15,
                "total": 75
            }
        ]
        
        benchmark_results = {}
        overall_start = time.time()
        
        for test_case in test_cases:
            print(f"\n📊 Testing: {test_case['name']}")
            
            result = self.run_concurrent_benchmark(
                test_case["endpoint"],
                test_case["concurrent"],
                test_case["total"]
            )
            
            benchmark_results[test_case["name"]] = result
            
            # Print immediate results
            if result.get("successful_requests", 0) > 0:
                print(f"   ✅ Success Rate: {result['success_rate_percent']:.1f}%")
                print(f"   ⚡ RPS: {result['requests_per_second']}")
                print(f"   🕐 Avg Latency: {result['latency_stats']['mean_ms']:.2f}ms")
                print(f"   📊 P95 Latency: {result['latency_stats']['p95_ms']:.2f}ms")
            else:
                print(f"   ❌ All requests failed")
                if result.get("sample_errors"):
                    print(f"   Sample errors: {result['sample_errors'][:2]}")
        
        overall_time = time.time() - overall_start
        
        # Calculate overall statistics
        total_requests = sum(r.get("total_requests", 0) for r in benchmark_results.values())
        total_successful = sum(r.get("successful_requests", 0) for r in benchmark_results.values())
        
        valid_rps = [r["requests_per_second"] for r in benchmark_results.values() if r.get("requests_per_second", 0) > 0]
        
        overall_stats = {
            "benchmark_summary": {
                "total_test_duration_seconds": round(overall_time, 3),
                "total_requests_across_all_tests": total_requests,
                "total_successful_requests": total_successful,
                "overall_success_rate_percent": (total_successful / total_requests * 100) if total_requests > 0 else 0,
                "average_rps_across_tests": round(statistics.mean(valid_rps), 2) if valid_rps else 0
            },
            "detailed_results": benchmark_results
        }
        
        return overall_stats


def analyze_performance(results: Dict[str, Any]):
    """Analyze and print performance results"""
    
    print("\n" + "=" * 60)
    print("📈 PERFORMANCE ANALYSIS REPORT")
    print("=" * 60)
    
    summary = results["benchmark_summary"]
    
    print(f"\n🎯 Overall Results:")
    print(f"   Total Duration: {summary['total_test_duration_seconds']}s")
    print(f"   Total Requests: {summary['total_requests_across_all_tests']:,}")
    print(f"   Successful Requests: {summary['total_successful_requests']:,}")
    print(f"   Success Rate: {summary['overall_success_rate_percent']:.1f}%")
    print(f"   Average RPS: {summary['average_rps_across_tests']}")
    
    # Performance grading
    avg_rps = summary['average_rps_across_tests']
    
    print(f"\n📊 Performance Assessment:")
    
    if avg_rps >= 5000:
        grade = "A+ (Excellent)"
        advice = "Great performance! Consider Go migration for even higher throughput."
    elif avg_rps >= 2000:
        grade = "A (Very Good)"
        advice = "Good performance. Optimize with uvloop and connection pooling."
    elif avg_rps >= 1000:
        grade = "B+ (Good)"
        advice = "Decent performance. Implement async optimizations."
    elif avg_rps >= 500:
        grade = "B (Acceptable)"
        advice = "Performance needs improvement. Add caching and optimize queries."
    elif avg_rps >= 100:
        grade = "C (Needs Improvement)"
        advice = "Performance issues detected. Consider framework optimization."
    else:
        grade = "D (Poor)"
        advice = "Critical performance problems. Major optimization needed."
    
    print(f"   Grade: {grade}")
    print(f"   Recommendation: {advice}")
    
    # Framework comparison
    print(f"\n🚀 Framework Performance Comparison (Estimated):")
    current_rps = avg_rps
    print(f"   Current FastAPI: ~{current_rps:.0f} RPS")
    print(f"   Optimized FastAPI (uvloop + optimizations): ~{current_rps * 2:.0f} RPS")
    print(f"   Node.js + Express: ~{current_rps * 1.5:.0f} RPS")
    print(f"   Go + Gin: ~{current_rps * 4:.0f} RPS")
    print(f"   Rust + Axum: ~{current_rps * 6:.0f} RPS")
    
    # Detailed breakdown
    print(f"\n📋 Detailed Test Results:")
    for test_name, result in results["detailed_results"].items():
        print(f"\n   📊 {test_name}:")
        if result.get("successful_requests", 0) > 0:
            print(f"     ✅ RPS: {result['requests_per_second']}")
            print(f"     🕐 Avg Latency: {result['latency_stats']['mean_ms']:.2f}ms")
            print(f"     📊 P95 Latency: {result['latency_stats']['p95_ms']:.2f}ms")
            print(f"     ✔️ Success Rate: {result['success_rate_percent']:.1f}%")
            print(f"     📦 Avg Response Size: {result['response_size_stats']['mean_bytes']:.0f} bytes")
        else:
            print(f"     ❌ Failed - {result.get('error', 'Unknown error')}")
    
    print("\n" + "=" * 60)


def main():
    """Main execution function"""
    
    print("🚀 Simple FastAPI Performance Benchmark")
    print("Testing current API implementation...")
    
    # Check if API is accessible
    benchmark = SimpleBenchmark()
    
    print("🔍 Checking API connectivity...")
    try:
        result = benchmark.make_request("/")
        if result["success"]:
            print("✅ API is running and accessible")
            print(f"   Status: {result['status_code']}")
            print(f"   Response time: {result['latency_ms']:.2f}ms")
        else:
            print(f"⚠️ API responded with error: {result.get('error', 'Unknown')}")
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        print("Please make sure your FastAPI server is running on http://localhost:8000")
        return
    
    # Run comprehensive benchmark
    try:
        print("\n🔥 Running comprehensive benchmark...")
        results = benchmark.comprehensive_benchmark()
        
        # Save results
        timestamp = int(time.time())
        filename = f"simple_benchmark_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Results saved to: {filename}")
        
        # Analyze results
        analyze_performance(results)
        
        # Recommendations
        print(f"\n🎯 Next Steps:")
        avg_rps = results["benchmark_summary"]["average_rps_across_tests"]
        
        if avg_rps < 1000:
            print("   🔧 Immediate Actions:")
            print("     1. Run the optimized FastAPI example (fastapi_performance_optimizations.py)")
            print("     2. Implement uvloop for async performance boost")
            print("     3. Add Redis caching for frequently accessed data")
            print("     4. Consider database query optimization")
        elif avg_rps < 3000:
            print("   🚀 Performance Improvements:")
            print("     1. Implement connection pooling")
            print("     2. Add response caching")
            print("     3. Consider async optimization techniques")
            print("     4. Monitor for bottlenecks")
        else:
            print("   ✅ Good Performance - Consider:")
            print("     1. Go migration for 3-5x performance boost")
            print("     2. Microservices architecture")
            print("     3. Load balancing for scaling")
        
        print(f"\n📚 Review the comprehensive analysis in: API_FRAMEWORK_ANALYSIS.md")
        
    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

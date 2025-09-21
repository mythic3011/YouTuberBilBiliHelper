#!/usr/bin/env python3
"""
Current FastAPI Performance Benchmark
Tests the performance of your existing FastAPI implementation.
"""

import asyncio
import aiohttp
import time
import statistics
import json
from typing import List, Dict, Any


class APIBenchmark:
    """Benchmark utility for testing API performance"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []
    
    async def make_request(self, session: aiohttp.ClientSession, endpoint: str) -> Dict[str, Any]:
        """Make a single request and measure performance"""
        start_time = time.time()
        
        try:
            async with session.get(f"{self.base_url}{endpoint}") as response:
                await response.read()
                latency = (time.time() - start_time) * 1000  # Convert to milliseconds
                
                return {
                    "success": True,
                    "status_code": response.status,
                    "latency_ms": latency,
                    "response_size": len(await response.read()) if response.status == 200 else 0
                }
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            return {
                "success": False,
                "status_code": 0,
                "latency_ms": latency,
                "error": str(e),
                "response_size": 0
            }
    
    async def run_concurrent_benchmark(
        self, 
        endpoint: str, 
        concurrent_requests: int = 10, 
        total_requests: int = 100
    ) -> Dict[str, Any]:
        """Run benchmark with concurrent requests"""
        
        print(f"🚀 Starting benchmark: {endpoint}")
        print(f"   Concurrent requests: {concurrent_requests}")
        print(f"   Total requests: {total_requests}")
        
        # Configure HTTP client
        connector = aiohttp.TCPConnector(
            limit=concurrent_requests * 2,
            limit_per_host=concurrent_requests
        )
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(
            connector=connector, 
            timeout=timeout
        ) as session:
            
            # Create semaphore for controlling concurrency
            semaphore = asyncio.Semaphore(concurrent_requests)
            
            async def make_request_with_semaphore():
                async with semaphore:
                    return await self.make_request(session, endpoint)
            
            # Run all requests
            start_time = time.time()
            
            results = await asyncio.gather(
                *[make_request_with_semaphore() for _ in range(total_requests)],
                return_exceptions=True
            )
            
            total_time = time.time() - start_time
            
            # Process results
            successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
            failed_results = [r for r in results if not (isinstance(r, dict) and r.get("success"))]
            
            if successful_results:
                latencies = [r["latency_ms"] for r in successful_results]
                response_sizes = [r["response_size"] for r in successful_results]
                
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
                        "p95_ms": round(statistics.quantiles(latencies, n=20)[18], 2) if len(latencies) > 20 else round(max(latencies), 2),
                        "p99_ms": round(statistics.quantiles(latencies, n=100)[98], 2) if len(latencies) > 100 else round(max(latencies), 2)
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
                    "error": "All requests failed"
                }
            
            return benchmark_results
    
    async def comprehensive_benchmark(self) -> Dict[str, Any]:
        """Run comprehensive benchmark across multiple endpoints"""
        
        print("🔥 Starting Comprehensive API Benchmark")
        print("=" * 60)
        
        # Test different endpoints
        test_cases = [
            {
                "name": "Health Check",
                "endpoint": "/api/v2/system/health",
                "concurrent": 50,
                "total": 500
            },
            {
                "name": "Simple API Endpoint",
                "endpoint": "/",
                "concurrent": 30,
                "total": 300
            },
            {
                "name": "Auth Status",
                "endpoint": "/api/v2/auth/status",
                "concurrent": 20,
                "total": 200
            }
        ]
        
        benchmark_results = {}
        overall_start = time.time()
        
        for test_case in test_cases:
            print(f"\n📊 Testing: {test_case['name']}")
            
            result = await self.run_concurrent_benchmark(
                test_case["endpoint"],
                test_case["concurrent"],
                test_case["total"]
            )
            
            benchmark_results[test_case["name"]] = result
            
            # Print summary
            if result.get("successful_requests", 0) > 0:
                print(f"   ✅ Success Rate: {result['success_rate_percent']:.1f}%")
                print(f"   ⚡ RPS: {result['requests_per_second']}")
                print(f"   🕐 Avg Latency: {result['latency_stats']['mean_ms']:.2f}ms")
                print(f"   📊 P95 Latency: {result['latency_stats']['p95_ms']:.2f}ms")
            else:
                print(f"   ❌ All requests failed")
        
        overall_time = time.time() - overall_start
        
        # Calculate overall statistics
        total_requests = sum(r.get("total_requests", 0) for r in benchmark_results.values())
        total_successful = sum(r.get("successful_requests", 0) for r in benchmark_results.values())
        
        overall_stats = {
            "benchmark_summary": {
                "total_test_duration_seconds": round(overall_time, 3),
                "total_requests_across_all_tests": total_requests,
                "total_successful_requests": total_successful,
                "overall_success_rate_percent": (total_successful / total_requests * 100) if total_requests > 0 else 0,
                "average_rps_across_tests": round(
                    statistics.mean([r["requests_per_second"] for r in benchmark_results.values() if r.get("requests_per_second", 0) > 0]), 2
                ) if any(r.get("requests_per_second", 0) > 0 for r in benchmark_results.values()) else 0
            },
            "detailed_results": benchmark_results
        }
        
        return overall_stats
    
    def print_performance_analysis(self, results: Dict[str, Any]):
        """Print detailed performance analysis"""
        
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
        
        print(f"\n📊 Performance Grades:")
        avg_rps = summary['average_rps_across_tests']
        
        if avg_rps >= 10000:
            grade = "A+ (Excellent)"
        elif avg_rps >= 5000:
            grade = "A (Very Good)"
        elif avg_rps >= 2000:
            grade = "B+ (Good)"
        elif avg_rps >= 1000:
            grade = "B (Acceptable)"
        elif avg_rps >= 500:
            grade = "C (Needs Improvement)"
        else:
            grade = "D (Poor Performance)"
        
        print(f"   Performance Grade: {grade}")
        
        print(f"\n🔧 Recommendations:")
        
        if avg_rps < 1000:
            print("   🚨 Critical Performance Issues:")
            print("     - Consider implementing uvloop")
            print("     - Add connection pooling")
            print("     - Optimize database queries")
            print("     - Consider caching strategies")
        elif avg_rps < 5000:
            print("   ⚠️ Performance Improvements Needed:")
            print("     - Implement async optimizations")
            print("     - Add Redis caching")
            print("     - Consider connection pooling")
        else:
            print("   ✅ Good Performance:")
            print("     - Consider Go migration for even better performance")
            print("     - Monitor for bottlenecks under higher load")
        
        print(f"\n📋 Detailed Test Results:")
        for test_name, result in results["detailed_results"].items():
            if result.get("successful_requests", 0) > 0:
                print(f"\n   {test_name}:")
                print(f"     RPS: {result['requests_per_second']}")
                print(f"     Avg Latency: {result['latency_stats']['mean_ms']:.2f}ms")
                print(f"     P95 Latency: {result['latency_stats']['p95_ms']:.2f}ms")
                print(f"     Success Rate: {result['success_rate_percent']:.1f}%")
        
        print("\n" + "=" * 60)


async def main():
    """Main benchmark execution"""
    
    print("🚀 FastAPI Performance Benchmark Tool")
    print("Testing current API implementation...")
    
    # Check if API is running
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/") as response:
                if response.status == 200:
                    print("✅ API is running and accessible")
                else:
                    print(f"⚠️ API returned status {response.status}")
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        print("Please make sure your FastAPI server is running on http://localhost:8000")
        return
    
    # Run benchmark
    benchmark = APIBenchmark()
    
    try:
        results = await benchmark.comprehensive_benchmark()
        
        # Save results to file
        timestamp = int(time.time())
        filename = f"benchmark_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n💾 Results saved to: {filename}")
        
        # Print analysis
        benchmark.print_performance_analysis(results)
        
        # Performance comparison with other frameworks
        print(f"\n🔥 Framework Performance Comparison:")
        print(f"   Current FastAPI: ~{results['benchmark_summary']['average_rps']:.0f} RPS")
        print(f"   Optimized FastAPI: ~{results['benchmark_summary']['average_rps'] * 2:.0f} RPS (estimated)")
        print(f"   Go + Gin: ~{results['benchmark_summary']['average_rps'] * 5:.0f} RPS (estimated)")
        print(f"   Rust + Axum: ~{results['benchmark_summary']['average_rps'] * 8:.0f} RPS (estimated)")
        
    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

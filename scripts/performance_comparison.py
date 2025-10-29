#!/usr/bin/env python3
"""
Performance Comparison: Python FastAPI vs Go Implementation
Comprehensive benchmarking script to compare both APIs
"""

import time
import json
import statistics
import threading
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime


class APIBenchmark:
    def __init__(self):
        self.results = {
            'python_fastapi': {'url': 'http://localhost:8000', 'results': []},
            'go_implementation': {'url': 'http://localhost:8001', 'results': []}
        }
    
    def make_request(self, url, timeout=10):
        """Make a single HTTP request and measure response time"""
        start_time = time.time()
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                data = response.read()
                status_code = response.status
                response_time = (time.time() - start_time) * 1000  # Convert to ms
                
                return {
                    'success': True,
                    'status_code': status_code,
                    'response_time_ms': response_time,
                    'response_size': len(data)
                }
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return {
                'success': False,
                'error': str(e),
                'response_time_ms': response_time,
                'response_size': 0
            }
    
    def test_endpoint(self, base_url, endpoint, num_requests=100, concurrent_threads=10):
        """Test a specific endpoint with concurrent requests"""
        url = f"{base_url}{endpoint}"
        results = []
        
        print(f"  🔥 Testing: {endpoint}")
        print(f"     URL: {url}")
        print(f"     Requests: {num_requests}, Threads: {concurrent_threads}")
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=concurrent_threads) as executor:
            futures = [executor.submit(self.make_request, url) for _ in range(num_requests)]
            
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
        
        total_time = time.time() - start_time
        
        # Calculate statistics
        successful_requests = [r for r in results if r['success']]
        failed_requests = [r for r in results if not r['success']]
        
        if successful_requests:
            response_times = [r['response_time_ms'] for r in successful_requests]
            response_sizes = [r['response_size'] for r in successful_requests]
            
            stats = {
                'endpoint': endpoint,
                'total_requests': num_requests,
                'successful_requests': len(successful_requests),
                'failed_requests': len(failed_requests),
                'success_rate': (len(successful_requests) / num_requests) * 100,
                'total_time_seconds': total_time,
                'requests_per_second': num_requests / total_time,
                'avg_response_time_ms': statistics.mean(response_times),
                'median_response_time_ms': statistics.median(response_times),
                'p95_response_time_ms': sorted(response_times)[int(0.95 * len(response_times))],
                'p99_response_time_ms': sorted(response_times)[int(0.99 * len(response_times))],
                'min_response_time_ms': min(response_times),
                'max_response_time_ms': max(response_times),
                'avg_response_size_bytes': statistics.mean(response_sizes),
                'concurrent_threads': concurrent_threads
            }
        else:
            stats = {
                'endpoint': endpoint,
                'total_requests': num_requests,
                'successful_requests': 0,
                'failed_requests': num_requests,
                'success_rate': 0,
                'requests_per_second': 0,
                'error': 'All requests failed'
            }
        
        print(f"     ✅ RPS: {stats.get('requests_per_second', 0):.1f}")
        print(f"     🕐 Avg Latency: {stats.get('avg_response_time_ms', 0):.2f}ms")
        print(f"     📊 Success Rate: {stats.get('success_rate', 0):.1f}%")
        
        return stats
    
    def benchmark_api(self, name, base_url):
        """Benchmark a specific API implementation"""
        print(f"\n🚀 Benchmarking: {name}")
        print(f"   Base URL: {base_url}")
        print("=" * 60)
        
        # Check if API is accessible
        try:
            self.make_request(f"{base_url}/health", timeout=5)
            print("   ✅ API is accessible")
        except Exception as e:
            print(f"   ❌ API not accessible: {e}")
            return None
        
        test_cases = [
            # Light load tests
            {'endpoint': '/health', 'requests': 50, 'threads': 5},
            {'endpoint': '/', 'requests': 100, 'threads': 10},
            
            # Medium load tests
            {'endpoint': '/health', 'requests': 200, 'threads': 20},
            {'endpoint': '/api/v2/system/health', 'requests': 150, 'threads': 15},
            
            # Heavy load tests
            {'endpoint': '/', 'requests': 500, 'threads': 50},
            {'endpoint': '/health', 'requests': 1000, 'threads': 100},
        ]
        
        api_results = []
        total_requests = 0
        total_time = 0
        total_successful = 0
        
        for test_case in test_cases:
            result = self.test_endpoint(
                base_url, 
                test_case['endpoint'], 
                test_case['requests'], 
                test_case['threads']
            )
            
            if result and 'total_time_seconds' in result:
                api_results.append(result)
                total_requests += result['total_requests']
                total_time += result['total_time_seconds']
                total_successful += result['successful_requests']
        
        # Calculate overall statistics
        if api_results:
            all_response_times = []
            all_rps = []
            
            for result in api_results:
                if 'requests_per_second' in result:
                    all_rps.append(result['requests_per_second'])
            
            overall_stats = {
                'name': name,
                'total_requests': total_requests,
                'total_successful': total_successful,
                'overall_success_rate': (total_successful / total_requests) * 100 if total_requests > 0 else 0,
                'average_rps': statistics.mean(all_rps) if all_rps else 0,
                'peak_rps': max(all_rps) if all_rps else 0,
                'individual_tests': api_results
            }
            
            return overall_stats
        
        return None
    
    def run_comparison(self):
        """Run complete performance comparison"""
        print("🎯 Performance Comparison: Python FastAPI vs Go Implementation")
        print("=" * 80)
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Test Python FastAPI
        python_results = self.benchmark_api(
            "Python FastAPI", 
            self.results['python_fastapi']['url']
        )
        
        # Test Go Implementation
        go_results = self.benchmark_api(
            "Go Implementation", 
            self.results['go_implementation']['url']
        )
        
        # Generate comparison report
        self.generate_comparison_report(python_results, go_results)
    
    def generate_comparison_report(self, python_results, go_results):
        """Generate detailed comparison report"""
        print("\n" + "=" * 80)
        print("📊 PERFORMANCE COMPARISON REPORT")
        print("=" * 80)
        
        if not python_results and not go_results:
            print("❌ No results available - both APIs failed to respond")
            return
        
        if not python_results:
            print("❌ Python FastAPI not accessible")
            python_results = {'name': 'Python FastAPI', 'average_rps': 0, 'peak_rps': 0, 'overall_success_rate': 0}
        
        if not go_results:
            print("❌ Go Implementation not accessible")
            go_results = {'name': 'Go Implementation', 'average_rps': 0, 'peak_rps': 0, 'overall_success_rate': 0}
        
        # Comparison summary
        print(f"\n🏆 PERFORMANCE SUMMARY:")
        print("-" * 40)
        
        python_avg_rps = python_results.get('average_rps', 0)
        go_avg_rps = go_results.get('average_rps', 0)
        
        python_peak_rps = python_results.get('peak_rps', 0)
        go_peak_rps = go_results.get('peak_rps', 0)
        
        print(f"Python FastAPI:")
        print(f"  📈 Average RPS: {python_avg_rps:.1f}")
        print(f"  🚀 Peak RPS: {python_peak_rps:.1f}")
        print(f"  ✅ Success Rate: {python_results.get('overall_success_rate', 0):.1f}%")
        
        print(f"\nGo Implementation:")
        print(f"  📈 Average RPS: {go_avg_rps:.1f}")
        print(f"  🚀 Peak RPS: {go_peak_rps:.1f}")
        print(f"  ✅ Success Rate: {go_results.get('overall_success_rate', 0):.1f}%")
        
        # Performance improvements
        if python_avg_rps > 0 and go_avg_rps > 0:
            avg_improvement = (go_avg_rps / python_avg_rps)
            peak_improvement = (go_peak_rps / python_peak_rps) if python_peak_rps > 0 else float('inf')
            
            print(f"\n🎯 PERFORMANCE IMPROVEMENTS:")
            print("-" * 40)
            print(f"Average RPS Improvement: {avg_improvement:.1f}x faster")
            print(f"Peak RPS Improvement: {peak_improvement:.1f}x faster")
            
            if avg_improvement >= 10:
                print("🏆 EXCELLENT: Go implementation delivers 10x+ performance!")
            elif avg_improvement >= 5:
                print("🚀 GREAT: Go implementation delivers 5x+ performance!")
            elif avg_improvement >= 2:
                print("✅ GOOD: Go implementation delivers 2x+ performance!")
            else:
                print("⚠️ MODEST: Performance improvement is less than 2x")
        
        # Expected vs Actual comparison
        print(f"\n📊 EXPECTED vs ACTUAL PERFORMANCE:")
        print("-" * 40)
        print(f"Expected Go RPS: ~15,000")
        print(f"Actual Go RPS: {go_avg_rps:.1f}")
        
        if go_avg_rps >= 15000:
            print("🎯 GOAL ACHIEVED: Go implementation meets performance targets!")
        elif go_avg_rps >= 10000:
            print("🚀 EXCELLENT: Go implementation exceeds 10,000 RPS!")
        elif go_avg_rps >= 5000:
            print("✅ GOOD: Go implementation exceeds 5,000 RPS!")
        else:
            print("📈 ROOM FOR IMPROVEMENT: Consider optimizations")
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"performance_comparison_{timestamp}.json"
        
        detailed_results = {
            'timestamp': datetime.now().isoformat(),
            'python_fastapi': python_results,
            'go_implementation': go_results,
            'summary': {
                'python_avg_rps': python_avg_rps,
                'go_avg_rps': go_avg_rps,
                'improvement_factor': go_avg_rps / python_avg_rps if python_avg_rps > 0 else 0,
                'go_target_achieved': go_avg_rps >= 15000
            }
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(detailed_results, f, indent=2)
            print(f"\n💾 Detailed results saved to: {filename}")
        except Exception as e:
            print(f"\n⚠️ Failed to save results: {e}")
        
        print("\n🎉 Performance comparison completed!")


def main():
    """Main benchmark execution"""
    benchmark = APIBenchmark()
    benchmark.run_comparison()


if __name__ == "__main__":
    main()


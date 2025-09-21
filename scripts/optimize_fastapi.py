#!/usr/bin/env python3
"""
FastAPI Optimization Implementation Script
Automatically applies performance optimizations to your existing FastAPI application.
"""

import os
import subprocess
import sys
from pathlib import Path


def install_performance_packages():
    """Install performance optimization packages"""
    print("📦 Installing performance packages...")
    
    packages = [
        "uvloop>=0.19.0",  # Event loop optimization
        "orjson>=3.9.0",   # Faster JSON serialization
        "httptools>=0.6.0", # Faster HTTP parsing
    ]
    
    for package in packages:
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", package], 
                         check=True, capture_output=True)
            print(f"  ✅ Installed {package}")
        except subprocess.CalledProcessError as e:
            print(f"  ❌ Failed to install {package}: {e}")
            return False
    
    return True


def update_main_py():
    """Update main.py with performance optimizations"""
    print("🔧 Updating main.py with optimizations...")
    
    main_py_path = Path("app/main.py")
    if not main_py_path.exists():
        print("  ❌ app/main.py not found")
        return False
    
    # Read current content
    with open(main_py_path, 'r') as f:
        content = f.read()
    
    # Check if already optimized
    if "uvloop.install()" in content:
        print("  ✅ uvloop already installed")
        return True
    
    # Add uvloop import and installation
    optimizations = """
# Performance optimizations
try:
    import uvloop
    uvloop.install()
    print("✅ uvloop enabled for better async performance")
except ImportError:
    print("⚠️ uvloop not available, using default event loop")

import orjson
from fastapi.responses import Response
"""
    
    # Find import section and add optimizations
    lines = content.split('\n')
    import_end = 0
    
    for i, line in enumerate(lines):
        if line.startswith('from app.') or line.startswith('import ') and not line.startswith('from'):
            import_end = i + 1
    
    # Insert optimizations after imports
    lines.insert(import_end, optimizations)
    
    # Write back
    with open(main_py_path, 'w') as f:
        f.write('\n'.join(lines))
    
    print("  ✅ Added uvloop and orjson optimizations")
    return True


def create_optimized_response_helper():
    """Create helper for optimized JSON responses"""
    print("📝 Creating optimized response helper...")
    
    helper_content = '''"""
Performance optimization helpers
"""

import orjson
from fastapi.responses import Response
from typing import Any, Dict


def fast_json_response(data: Any) -> Response:
    """Create optimized JSON response using orjson"""
    return Response(
        content=orjson.dumps(data),
        media_type="application/json",
        headers={"X-Optimized": "orjson"}
    )


def create_cached_response(data: Any, cache_control: str = "public, max-age=300") -> Response:
    """Create cached JSON response"""
    return Response(
        content=orjson.dumps(data),
        media_type="application/json",
        headers={
            "Cache-Control": cache_control,
            "X-Optimized": "orjson-cached"
        }
    )
'''
    
    helpers_path = Path("app/optimizations.py")
    with open(helpers_path, 'w') as f:
        f.write(helper_content)
    
    print(f"  ✅ Created {helpers_path}")
    return True


def update_dockerfile():
    """Update Dockerfile with performance optimizations"""
    print("🐳 Updating Dockerfile...")
    
    dockerfile_path = Path("Dockerfile")
    if not dockerfile_path.exists():
        print("  ❌ Dockerfile not found")
        return False
    
    # Read current content
    with open(dockerfile_path, 'r') as f:
        content = f.read()
    
    # Check if already optimized
    if "--loop uvloop" in content:
        print("  ✅ Dockerfile already optimized")
        return True
    
    # Update CMD line to use uvloop
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('CMD') and 'uvicorn' in line:
            # Add uvloop to uvicorn command
            if "--loop uvloop" not in line:
                lines[i] = line.replace('"uvicorn"', '"uvicorn"').replace(
                    'app.main:app"', 'app.main:app", "--loop", "uvloop"'
                )
                break
    
    # Add environment variable
    env_added = False
    for i, line in enumerate(lines):
        if line.startswith('ENV') and 'PATH' in line:
            lines.insert(i + 1, 'ENV UVLOOP_ENABLED=true')
            env_added = True
            break
    
    if not env_added:
        # Add before CMD
        for i, line in enumerate(lines):
            if line.startswith('CMD'):
                lines.insert(i, 'ENV UVLOOP_ENABLED=true')
                break
    
    # Write back
    with open(dockerfile_path, 'w') as f:
        f.write('\n'.join(lines))
    
    print("  ✅ Updated Dockerfile with uvloop optimization")
    return True


def update_docker_compose():
    """Update docker-compose.yml with performance settings"""
    print("📋 Updating docker-compose.yml...")
    
    compose_path = Path("docker-compose.yml")
    if not compose_path.exists():
        print("  ❌ docker-compose.yml not found")
        return False
    
    # Read current content
    with open(compose_path, 'r') as f:
        content = f.read()
    
    # Check if already optimized
    if "UVLOOP_ENABLED=true" in content:
        print("  ✅ docker-compose.yml already optimized")
        return True
    
    # Add performance environment variables
    lines = content.split('\n')
    
    # Find app service environment section
    in_app_service = False
    in_environment = False
    env_indent = "      "
    
    for i, line in enumerate(lines):
        if 'app:' in line or 'service:' in line:
            in_app_service = True
        elif in_app_service and line.strip().startswith('environment:'):
            in_environment = True
        elif in_app_service and in_environment and line.startswith(env_indent + '- '):
            # Add performance variables after existing environment vars
            continue
        elif in_app_service and in_environment and (line.strip() == '' or not line.startswith(env_indent)):
            # End of environment section, add our variables
            perf_vars = [
                f"{env_indent}- UVLOOP_ENABLED=true",
                f"{env_indent}- PYTHONUNBUFFERED=1",
                f"{env_indent}- ASYNC_POOL_SIZE=100"
            ]
            
            for var in perf_vars:
                lines.insert(i, var)
                i += 1
            
            break
    
    # Write back
    with open(compose_path, 'w') as f:
        f.write('\n'.join(lines))
    
    print("  ✅ Updated docker-compose.yml with performance settings")
    return True


def create_performance_middleware():
    """Create performance monitoring middleware"""
    print("📊 Creating performance monitoring middleware...")
    
    middleware_content = '''"""
Performance monitoring middleware
"""

import time
import logging
from fastapi import Request
from fastapi.responses import Response

logger = logging.getLogger(__name__)


async def performance_monitoring_middleware(request: Request, call_next):
    """Monitor request performance and add metrics headers"""
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate metrics
    process_time = time.time() - start_time
    
    # Add performance headers
    response.headers["X-Process-Time"] = f"{process_time:.3f}"
    response.headers["X-Optimized"] = "true"
    
    # Log slow requests
    if process_time > 1.0:  # Log requests taking more than 1 second
        logger.warning(
            f"Slow request: {request.method} {request.url} took {process_time:.3f}s"
        )
    
    return response


def setup_performance_monitoring(app):
    """Setup performance monitoring for the FastAPI app"""
    app.middleware("http")(performance_monitoring_middleware)
    logger.info("✅ Performance monitoring middleware enabled")
'''
    
    middleware_path = Path("app/performance_middleware.py")
    with open(middleware_path, 'w') as f:
        f.write(middleware_content)
    
    print(f"  ✅ Created {middleware_path}")
    return True


def run_benchmark():
    """Run performance benchmark to test optimizations"""
    print("🚀 Running performance benchmark...")
    
    benchmark_script = Path("examples/simple_benchmark.py")
    if not benchmark_script.exists():
        print("  ❌ Benchmark script not found")
        return False
    
    try:
        # Run benchmark
        result = subprocess.run(
            [sys.executable, str(benchmark_script)],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            # Extract RPS from output
            lines = result.stdout.split('\n')
            for line in lines:
                if "Average RPS:" in line:
                    rps = line.split("Average RPS:")[1].strip()
                    print(f"  📈 Performance: {rps}")
                    break
            
            print("  ✅ Benchmark completed successfully")
            return True
        else:
            print(f"  ❌ Benchmark failed: {result.stderr}")
            return False
    
    except subprocess.TimeoutExpired:
        print("  ⏰ Benchmark timed out")
        return False
    except Exception as e:
        print(f"  ❌ Benchmark error: {e}")
        return False


def main():
    """Main optimization process"""
    print("🚀 FastAPI Performance Optimization Script")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not Path("app/main.py").exists():
        print("❌ Please run this script from the project root directory")
        print("   (where app/main.py is located)")
        sys.exit(1)
    
    print("📍 Project directory confirmed")
    
    steps = [
        ("Installing performance packages", install_performance_packages),
        ("Updating main.py", update_main_py),
        ("Creating response helpers", create_optimized_response_helper),
        ("Updating Dockerfile", update_dockerfile),
        ("Updating docker-compose.yml", update_docker_compose),
        ("Creating performance middleware", create_performance_middleware),
    ]
    
    success_count = 0
    total_steps = len(steps)
    
    for step_name, step_func in steps:
        print(f"\n🔧 {step_name}...")
        if step_func():
            success_count += 1
        else:
            print(f"  ⚠️ Step failed: {step_name}")
    
    print(f"\n" + "=" * 60)
    print(f"📊 Optimization Results: {success_count}/{total_steps} steps completed")
    
    if success_count == total_steps:
        print("🎉 All optimizations applied successfully!")
        print("\n📋 Next Steps:")
        print("1. Rebuild containers: docker-compose build")
        print("2. Restart services: docker-compose up -d")
        print("3. Run benchmark: python3 examples/simple_benchmark.py")
        print("4. Expected improvement: 2-3x performance boost")
        
        # Offer to rebuild containers
        if input("\n🔄 Rebuild containers now? (y/n): ").lower() == 'y':
            print("🏗️ Rebuilding containers...")
            try:
                subprocess.run(["docker-compose", "build"], check=True)
                print("✅ Containers rebuilt successfully")
                
                if input("🚀 Restart services? (y/n): ").lower() == 'y':
                    subprocess.run(["docker-compose", "up", "-d"], check=True)
                    print("✅ Services restarted")
                    
                    # Wait and run benchmark
                    print("⏳ Waiting 10 seconds for services to start...")
                    import time
                    time.sleep(10)
                    run_benchmark()
                    
            except subprocess.CalledProcessError as e:
                print(f"❌ Container rebuild failed: {e}")
    
    else:
        print("⚠️ Some optimizations failed. Check the output above.")
        print("💡 You can still apply the successful optimizations manually.")
    
    print("\n📚 For more information, see:")
    print("   - API_FRAMEWORK_ANALYSIS.md")
    print("   - FINAL_RECOMMENDATIONS.md")
    print("   - examples/fastapi_performance_optimizations.py")


if __name__ == "__main__":
    main()

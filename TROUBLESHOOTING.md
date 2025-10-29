# 🔧 Troubleshooting Guide

Quick fixes for common issues with `manage.sh`

> **Note:** This project uses `uv` for faster Python package management. Install it with:
> ```bash
> curl -LsSf https://astral.sh/uv/install.sh | sh
> ```

---

## ✅ Quick Tests

### Test 1: Check if script is executable

```bash
ls -la manage.sh
# Should show: -rwxr-xr-x
```

**Fix if needed:**

```bash
chmod +x manage.sh
```

### Test 2: Test basic command

```bash
./manage.sh help
```

### Test 3: Check status

```bash
./manage.sh status
```

---

## 🐛 Common Issues & Fixes

### Issue 1: "Permission denied"

**Error:**

```
bash: ./manage.sh: Permission denied
```

**Fix:**

```bash
chmod +x manage.sh
./manage.sh help
```

---

### Issue 2: "command not found" (running without ./)

**Error:**

```
manage.sh: command not found
```

**Fix:**
Use `./` before the script:

```bash
./manage.sh dev      # ✓ Correct
manage.sh dev        # ✗ Wrong
```

Or add to PATH:

```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$PATH:$PWD"
```

---

### Issue 3: Docker not running

**Error:**

```
Cannot connect to the Docker daemon
```

**Fix:**

```bash
# Start Docker Desktop (macOS)
open -a Docker

# Or check if Docker is running
docker ps

# If Docker is not installed:
# Download from: https://www.docker.com/products/docker-desktop
```

---

### Issue 4: Port already in use

**Error:**

```
Port 8000 is already in use
```

**Fix:**

```bash
# Find what's using the port
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port
# Edit docker-compose.yml to change ports
```

---

### Issue 5: Python virtual environment issues

**Error:**

```
ModuleNotFoundError: No module named 'fastapi'
```

**Fix:**

```bash
# Clean and recreate
./manage.sh clean all

# Start fresh
./manage.sh dev
```

---

### Issue 6: Docker Compose v1 vs v2

**Error:**

```
docker-compose: command not found
```

**Fix Option 1** - Install Docker Compose v1:

```bash
# macOS with Homebrew
brew install docker-compose
```

**Fix Option 2** - Use Docker Compose v2 (built into Docker):

```bash
# Edit manage.sh and replace:
docker-compose    →    docker compose
```

---

### Issue 7: Services won't start

**Symptoms:**

- `./manage.sh start` fails
- Containers exit immediately

**Diagnosis:**

```bash
# Check Docker logs
./manage.sh logs all

# Check Docker status
docker ps -a

# Check for errors
docker-compose logs --tail=50
```

**Fix:**

```bash
# Clean everything
./manage.sh clean docker

# Rebuild
./manage.sh build all

# Try again
./manage.sh start python
```

---

### Issue 8: "lsof: command not found"

**Error:**

```
manage.sh: line X: lsof: command not found
```

**Fix:**
The script will still work, but port checking is disabled.

**Install lsof:**

```bash
# macOS (should be pre-installed)
# If missing, install Xcode Command Line Tools:
xcode-select --install

# Linux
sudo apt-get install lsof  # Debian/Ubuntu
sudo yum install lsof      # CentOS/RHEL
```

---

### Issue 9: Tests failing

**Error:**

```
pytest: command not found
```

**Fix:**

```bash
# Make sure you're in development mode
./manage.sh dev

# Or install dependencies manually
pip install -e .
pip install -r requirements-dev.txt

# Then run tests
./manage.sh test unit
```

---

### Issue 10: Redis connection refused

**Error:**

```
Error: Redis connection refused
```

**Fix:**

```bash
# Start Redis
./manage.sh start python  # This starts Redis too

# Or manually
docker-compose up -d redis

# Check if Redis is running
./manage.sh status
```

---

## 🔍 Debugging Steps

### Step 1: Check script syntax

```bash
bash -n manage.sh
# No output = syntax is OK
```

### Step 2: Run with debug mode

```bash
bash -x ./manage.sh status
# Shows each command as it executes
```

### Step 3: Check all dependencies

```bash
# Required tools
which python3
which docker
which docker-compose
which pytest
which redis-cli
```

### Step 4: Check Docker

```bash
# Docker running?
docker ps

# Docker Compose working?
docker-compose version

# Any containers?
docker ps -a
```

### Step 5: Check Python environment

```bash
# Virtual environment exists?
ls -la .venv

# Python version
python3 --version

# Installed packages
pip list | grep fastapi
```

---

## 🚑 Emergency Fixes

### Nuclear Option 1: Clean Everything

```bash
./manage.sh clean all
./manage.sh dev
```

### Nuclear Option 2: Full Reset

```bash
# Stop everything
./manage.sh stop

# Clean everything
./manage.sh clean all

# Remove Docker images
docker-compose down -v --rmi all

# Rebuild from scratch
./manage.sh build all
./manage.sh deploy go
```

### Nuclear Option 3: Manual Setup

```bash
# If manage.sh doesn't work at all,
# use manual commands:

# Start Python API manually
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -r requirements-dev.txt
uvicorn app.main:app --reload

# Or use Docker Compose directly
docker-compose up -d python-api redis
```

---

## 📝 Getting Help

### Collect Debug Info

Run this to collect debug information:

```bash
cat << 'EOF' > debug-info.txt
=== System Info ===
OS: $(uname -a)
Shell: $SHELL
Python: $(python3 --version)
Docker: $(docker --version)
Docker Compose: $(docker-compose --version)

=== File Permissions ===
$(ls -la manage.sh)

=== Docker Status ===
$(docker ps -a)

=== Recent Logs ===
$(docker-compose logs --tail=20 2>&1)

=== Port Status ===
$(lsof -i :8000 2>&1)
$(lsof -i :8001 2>&1)
$(lsof -i :6379 2>&1)
EOF

cat debug-info.txt
```

### Common Questions

**Q: Which command should I use for development?**

```bash
./manage.sh dev
```

**Q: Which command for production?**

```bash
./manage.sh deploy go
```

**Q: How do I check if it's running?**

```bash
./manage.sh status
```

**Q: How do I see logs?**

```bash
./manage.sh logs all
```

**Q: How do I stop everything?**

```bash
./manage.sh stop
```

**Q: How do I start over?**

```bash
./manage.sh clean all
./manage.sh dev
```

---

## 🎯 Specific Command Issues

### `./manage.sh dev` fails

**Check:**

1. Is Python 3.12+ installed? `python3 --version`
2. Can create virtual environment? `python3 -m venv test_venv`
3. Is port 8000 free? `lsof -i :8000`

**Try:**

```bash
# Manual dev setup
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

### `./manage.sh start` fails

**Check:**

1. Is Docker running? `docker ps`
2. Are ports free? `lsof -i :8000 :8001 :6379`
3. Do Docker images exist? `docker images | grep video-api`

**Try:**

```bash
# Manual start
docker-compose up -d python-api redis

# Or Go API
cd go-api && docker-compose up -d
```

### `./manage.sh test` fails

**Check:**

1. Are dependencies installed? `pip list | grep pytest`
2. Is Redis running? `./manage.sh status`
3. Are tests present? `ls tests/`

**Try:**

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run pytest directly
pytest tests/unit/ -v
```

---

## 💡 Pro Tips

1. **Always check status first:**

   ```bash
   ./manage.sh status
   ```

2. **View logs when debugging:**

   ```bash
   ./manage.sh logs all
   ```

3. **Clean between attempts:**

   ```bash
   ./manage.sh clean temp
   ```

4. **Use verbose Docker output:**

   ```bash
   docker-compose up     # Without -d to see logs
   ```

5. **Test with simple commands first:**
   ```bash
   ./manage.sh help      # Should always work
   ./manage.sh status    # Check current state
   ```

---

## 📞 Still Having Issues?

If you're still having problems:

1. **Gather debug info** (see "Getting Help" section above)
2. **Check the error message carefully**
3. **Try the "Nuclear Options" above**
4. **Use manual commands** as a fallback

**Alternative: Use Makefile**

```bash
# The project also has a Makefile
make help
make dev
make test
```

**Alternative: Use individual scripts**

```bash
# Scripts are also available
./scripts/quick-deploy.sh python
./scripts/compare_apis.sh
./scripts/setup-dev.sh
```

---

**Remember:** Most issues are solved by:

1. `./manage.sh clean all`
2. `./manage.sh dev`

---

**Last Updated:** October 30, 2025

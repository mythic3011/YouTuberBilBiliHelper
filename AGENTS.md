# Project Context Handoff for Claude

## Developer Profile
PolyU CS student (postgrad-level), Hong Kong-based. Full-stack web, Go backends, cybersecurity/DevOps, Docker/K8s. Heavy Git user with pre-commit hooks (block .env/keys) + conventional commits.

**CRITICAL**: Full "git *" access allowed. NO "Co-Authored-By: Claude" in commits—keep authorship clean.

## Active Projects

### Portfolio/Links Backend (Go) [Current focus]
- HTTP handlers: links/portfolio endpoints
- Auth middleware, user-agent parsing (mssola/user_agent)
- PDF access via email context
- GitHub: mythic3011/portfolio

### Medical All-in-One App (ELC Fund Proposal)
- Clinics/hospitals/doctors aggregation
- A&E wait times + symptom→dept routing
- Reviews via API/link-out (no scraping)
- Target: elderly/caregivers

### PHP/Laravel Web Apps
- Docker-deployed admin panels
- Install wizard, 2FA, auditing, permissions
- Framework config exceptions allowed

### Node.js/Express SPAs
- Tailwind/daisyUI + Sequelize ORM
- Bootstrap 5 fallback option

### ML/AI Tools **MANDATORY: uv only**
- Python (PyTorch/diffusers): comic/manga OCR/translation/colorization
- ALWAYS: `uv pip install`, `uv run script.py`. Never pip/venv.

### Cybersecurity CTF
- PolyU x NuttyShell 2025 winner (Sub-Degree)
- Network sec, CrowdSec/Nginx, k3s hardening
- Other: Comic translation, IoT auditing, VRChat/Warframe tooling

## Tech Stack
- **Backend**: Go (primary), PHP/Laravel, Node/Express, Python ML (uv only)
- **Frontend**: Tailwind, JS (Livewire?)
- **Infra**: Docker Compose/K3s, PostgreSQL/MySQL, Nginx
- **Env**: macOS/WSL/Ubuntu, GitHub (mythic3011)

## Agent Permissions
✅ `Bash(git *)` - all git commands
✅ `go test/get/mod *`
✅ Python: `uv pip install/run` only
❌ No Claude co-author commits

---

**Next**: Code reviews, features, Git commits for [project]?

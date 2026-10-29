#!/usr/bin/env bash

set -e

PROJECT_ROOT="$(pwd)"

echo "=============================================="
echo " Getto Platform - Backend Structure Setup"
echo "=============================================="
echo
echo "Project root: $PROJECT_ROOT"
echo

# -------------------------------------------------
# 1. Verify project root
# -------------------------------------------------

if [ ! -d "$PROJECT_ROOT/frontend" ]; then
    echo "ERROR: frontend/ directory was not found."
    echo "Run this script from:"
    echo "~/Documents/getto-platform"
    exit 1
fi

echo "[OK] Existing frontend/ directory found."
echo

# -------------------------------------------------
# 2. Create main project directories
# -------------------------------------------------

echo "Creating project directories..."

mkdir -p backend
mkdir -p database/erd
mkdir -p database/documentation
mkdir -p database/seed_data
mkdir -p database/postgis

mkdir -p storage/images
mkdir -p storage/videos
mkdir -p storage/documents
mkdir -p storage/temp

mkdir -p docs/requirements
mkdir -p docs/architecture
mkdir -p docs/api
mkdir -p docs/database
mkdir -p docs/workflows

mkdir -p scripts

echo "[OK] Main directories created."
echo

# -------------------------------------------------
# 3. Create backend Python virtual environment
# -------------------------------------------------

cd "$PROJECT_ROOT/backend"

if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
else
    echo "[OK] Python virtual environment already exists."
fi

echo

# -------------------------------------------------
# 4. Activate virtual environment
# -------------------------------------------------

source .venv/bin/activate

echo "[OK] Python virtual environment activated."
echo

# -------------------------------------------------
# 5. Upgrade pip
# -------------------------------------------------

echo "Updating pip..."

python -m pip install --upgrade pip

# -------------------------------------------------
# 6. Install backend packages
# -------------------------------------------------

echo
echo "Installing Django, Django REST Framework and PostgreSQL packages..."

pip install \
    django \
    djangorestframework \
    django-cors-headers \
    psycopg[binary] \
    python-dotenv \
    PyJWT \
    argon2-cffi

echo
echo "[OK] Backend packages installed."
echo

# -------------------------------------------------
# 7. Create requirements file
# -------------------------------------------------

pip freeze > requirements.txt

echo "[OK] requirements.txt created."
echo

# -------------------------------------------------
# 8. Initialize Django project
# -------------------------------------------------

if [ ! -f "manage.py" ]; then

    echo "Creating Django project..."

    django-admin startproject config .

else

    echo "[OK] Django manage.py already exists."
fi

echo

# -------------------------------------------------
# 9. Create Django applications
# -------------------------------------------------

APPS=(
    users
    authentication
    customers
    house_owners
    staff
    properties
    locations
    payments
    notifications
)

echo "Creating Django applications..."

for APP in "${APPS[@]}"; do

    if [ ! -d "apps/$APP" ]; then

        mkdir -p apps

        python manage.py startapp "$APP" "apps/$APP"

        echo "  Created: apps/$APP"

    else

        echo "  Exists:  apps/$APP"

    fi

done

echo
echo "[OK] Django applications created."
echo

# -------------------------------------------------
# 10. Create API structure
# -------------------------------------------------

echo "Creating API structure..."

mkdir -p api/v1

touch api/__init__.py
touch api/v1/__init__.py

echo "[OK] API structure created."
echo

# -------------------------------------------------
# 11. Create test structure
# -------------------------------------------------

mkdir -p tests

touch tests/__init__.py

echo "[OK] Test directory created."
echo

# -------------------------------------------------
# 12. Create requirements directory
# -------------------------------------------------

mkdir -p requirements

if [ ! -f requirements/base.txt ]; then
    cp requirements.txt requirements/base.txt
fi

touch requirements/development.txt
touch requirements/production.txt

echo "[OK] Requirements structure created."
echo

# -------------------------------------------------
# 13. Create .env.example
# -------------------------------------------------

if [ ! -f ".env.example" ]; then

cat > .env.example <<'EOF'
# ==========================================
# Django
# ==========================================

DJANGO_DEBUG=True
DJANGO_SECRET_KEY=change-this-secret-key
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# ==========================================
# PostgreSQL
# ==========================================

DB_NAME=getto_db
DB_USER=getto
DB_PASSWORD=change-this-password
DB_HOST=127.0.0.1
DB_PORT=5432

# ==========================================
# API
# ==========================================

API_VERSION=v1

# ==========================================
# Email / SMTP
# ==========================================

EMAIL_HOST=
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=True

# ==========================================
# SMS
# ==========================================

SMS_API_URL=
SMS_API_KEY=

# ==========================================
# Payment Gateway
# ==========================================

PAYMENT_GATEWAY_URL=
PAYMENT_GATEWAY_API_KEY=
PAYMENT_GATEWAY_SECRET=

# ==========================================
# Local Storage
# ==========================================

MEDIA_ROOT=storage
MEDIA_URL=/media/
EOF

fi

echo "[OK] .env.example created."
echo

# -------------------------------------------------
# 14. Create backend directories for services
# -------------------------------------------------

mkdir -p core
mkdir -p services
mkdir -p repositories
mkdir -p utils

touch core/__init__.py
touch services/__init__.py
touch repositories/__init__.py
touch utils/__init__.py

echo "[OK] Backend supporting directories created."
echo

# -------------------------------------------------
# 15. Create storage documentation
# -------------------------------------------------

cd "$PROJECT_ROOT"

cat > storage/README.md <<'EOF'
# Getto Platform Local Storage

Uploaded files are stored locally during development.

Directories:

- images/     - profile photos and other images
- videos/     - uploaded videos
- documents/  - PDF and other documents
- temp/       - temporary uploaded files

Do not store application source code here.

Production storage can later be changed without changing
the business logic by implementing a storage service.
EOF

# -------------------------------------------------
# 16. Create API documentation placeholder
# -------------------------------------------------

cat > docs/api/API_CONTRACT.md <<'EOF'
# Getto Platform API Contract

API base path:

/api/v1/

The backend developer is responsible for maintaining
stable API contracts.

Every endpoint should document:

- HTTP method
- URL
- Authentication requirement
- Permissions
- Request parameters
- Request body
- Response body
- HTTP status codes
- Validation errors
- Error responses

Frontend developers should integrate with documented
API contracts rather than directly accessing PostgreSQL.
EOF

# -------------------------------------------------
# 17. Create database documentation
# -------------------------------------------------

cat > database/README.md <<'EOF'
# Getto Platform Database

Database engine:

PostgreSQL

Spatial extension:

PostGIS

Database schema changes are managed through Django migrations.

Database designer responsibilities:

- ERD
- Tables
- Relationships
- Constraints
- Indexes
- PostgreSQL/PostGIS design
- Database documentation

The frontend must never connect directly to PostgreSQL.

The backend communicates with PostgreSQL through Django ORM.
EOF

# -------------------------------------------------
# 18. Create development workflow document
# -------------------------------------------------

cat > docs/workflows/DEVELOPMENT_WORKFLOW.md <<'EOF'
# Getto Platform Development Workflow

Requirements
    ↓
Database Design
    ↓
Backend API Contract
    ↓
Backend Implementation
    ↓
Frontend Implementation
    ↓
Unit Testing
    ↓
API Testing
    ↓
Frontend/API Integration
    ↓
System Integration Testing
    ↓
User Acceptance Testing
    ↓
Deployment

Developers must work through Git branches and pull requests.

Do not directly push feature work to main.
EOF

# -------------------------------------------------
# 19. Create CONTRIBUTING.md
# -------------------------------------------------

cat > CONTRIBUTING.md <<'EOF'
# Contributing to Getto Platform

## Branches

Use feature branches.

Examples:

feature/backend-authentication
feature/backend-customers
feature/frontend-dashboard
feature/frontend-properties
feature/database-schema

## Workflow

1. Pull latest develop branch.
2. Create a feature branch.
3. Implement the assigned feature.
4. Test locally.
5. Commit changes.
6. Push the branch.
7. Create a Pull Request.
8. Code review.
9. Fix review issues.
10. Merge into develop.

Do not directly push feature work to main.
EOF

# -------------------------------------------------
# 20. Create root .gitignore if missing
# -------------------------------------------------

if [ ! -f "$PROJECT_ROOT/.gitignore" ]; then

cat > "$PROJECT_ROOT/.gitignore" <<'EOF'
# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd

# Virtual environment
backend/.venv/

# Django
*.log
db.sqlite3
staticfiles/

# Environment
.env
.env.*

# Local uploaded files
storage/images/*
storage/videos/*
storage/documents/*
storage/temp/*

# Keep storage directory structure
!storage/images/.gitkeep
!storage/videos/.gitkeep
!storage/documents/.gitkeep
!storage/temp/.gitkeep

# Node
node_modules/
.next/
out/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db
EOF

fi

# -------------------------------------------------
# 21. Create .gitkeep files
# -------------------------------------------------

touch storage/images/.gitkeep
touch storage/videos/.gitkeep
touch storage/documents/.gitkeep
touch storage/temp/.gitkeep

# -------------------------------------------------
# 22. Final structure
# -------------------------------------------------

echo
echo "=============================================="
echo " Setup completed successfully"
echo "=============================================="
echo

echo "Project structure:"
find "$PROJECT_ROOT" \
    -maxdepth 3 \
    -type d \
    ! -path "*/frontend/node_modules*" \
    ! -path "*/frontend/.next*" \
    ! -path "*/backend/.venv*" \
    | sort

echo
echo "Backend:"
echo "  cd backend"
echo "  source .venv/bin/activate"
echo "  python manage.py check"
echo
echo "Next step:"
echo "  Configure Django PostgreSQL/PostGIS connection."
echo

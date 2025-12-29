#!/bin/bash

# Script to create a clean CI/CD pipeline repository
# Run this script to copy all necessary files to a new directory

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Creating CI/CD Pipeline Repository${NC}"
echo "=================================================="

# Get target directory from user or use default
TARGET_DIR="${1:-../passport-photo-ai-cicd}"

echo -e "${YELLOW}📁 Target directory: ${TARGET_DIR}${NC}"

# Create target directory
mkdir -p "$TARGET_DIR"

echo -e "${BLUE}📋 Copying essential files...${NC}"

# Copy GitHub Actions workflow
echo "  → .github/workflows/"
mkdir -p "$TARGET_DIR/.github/workflows"
cp -r .github/workflows/* "$TARGET_DIR/.github/workflows/"

# Copy all scripts
echo "  → scripts/"
cp -r scripts "$TARGET_DIR/"

# Copy test images
echo "  → test_images/"
cp -r test_images "$TARGET_DIR/"

# Copy database module
echo "  → database/"
cp -r database "$TARGET_DIR/"

# Copy services module
echo "  → services/"
cp -r services "$TARGET_DIR/"

# Copy core application files
echo "  → Core application files"
cp application.py "$TARGET_DIR/"
cp requirements.txt "$TARGET_DIR/"
cp cloudformation-enhanced.yaml "$TARGET_DIR/"
cp cors_config.py "$TARGET_DIR/"

# Copy documentation
echo "  → Documentation"
cp CI-CD-PIPELINE-README.md "$TARGET_DIR/README.md"
cp GITHUB_REPO_SETUP.md "$TARGET_DIR/"

# Create .gitignore
echo "  → .gitignore"
cat > "$TARGET_DIR/.gitignore" << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
venv/
env/
ENV/
.venv/
.env

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Testing
.coverage
.pytest_cache/
.tox/
htmlcov/
test-results/
logs/

# Deployment
source-bundle.zip
deployment-info.json
deployment-url.txt
*.tmp
temp-*

# AWS
.aws/
aws-credentials.json

# CI/CD Pipeline Results
test-results/
logs/
*.log
error-report.json
*-results.json

# Local development
.env.local
.env.development
.env.test
.env.production

# Backup files
*_backup*
backup_*
*.bak
EOF

# Initialize git repository
echo -e "${BLUE}🔧 Initializing Git repository...${NC}"
cd "$TARGET_DIR"
git init
git add .
git commit -m "Initial commit: Complete CI/CD pipeline with ML/AI testing

Features:
- GitHub Actions workflow for automated deployment
- Pre-deployment validation (dependencies, security, ML/AI)
- Infrastructure provisioning with CloudFormation
- Application deployment to Elastic Beanstalk
- Post-deployment verification and testing
- Error handling and recovery mechanisms
- Multi-environment support (dev/staging/prod)
- Comprehensive ML/AI testing with test images"

echo -e "${GREEN}✅ Repository created successfully!${NC}"
echo ""
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo "1. Create a new GitHub repository"
echo "2. Add the repository as remote:"
echo "   ${BLUE}git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git${NC}"
echo "3. Push to GitHub:"
echo "   ${BLUE}git branch -M main${NC}"
echo "   ${BLUE}git push -u origin main${NC}"
echo "4. Configure GitHub Secrets (see GITHUB_REPO_SETUP.md)"
echo "5. Trigger the pipeline!"
echo ""
echo -e "${GREEN}🎉 Your CI/CD pipeline is ready to deploy!${NC}"

# Return to original directory
cd - > /dev/null

echo -e "${BLUE}📍 Repository location: ${TARGET_DIR}${NC}"
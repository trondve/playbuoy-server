#!/bin/bash
# deploy.sh
# Deploy changes from this repo to Raspberry Pi FastAPI server
# Usage: bash tools/scripts/deploy.sh [target] [branch]

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
TARGET="${1:-playbuoyadmin@192.168.140.7}"
BRANCH="${2:-main}"
REMOTE_PATH="/home/playbuoyadmin/playbuoy-server"
REMOTE_BACKUP_PATH="/home/playbuoyadmin/playbuoy-backup-$(date +%Y%m%d-%H%M%S)"

echo -e "${YELLOW}======================================${NC}"
echo -e "${YELLOW}PlayBuoy Deployment Script${NC}"
echo -e "${YELLOW}======================================${NC}"
echo ""
echo "Target:  $TARGET"
echo "Branch:  $BRANCH"
echo "Path:    $REMOTE_PATH"
echo ""

# Step 1: Verify we're in the repo
if [ ! -d ".git" ]; then
    echo -e "${RED}✗ Not in a git repository. Run from project root.${NC}"
    exit 1
fi

# Step 2: Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${RED}✗ Uncommitted changes detected. Commit first:${NC}"
    echo "  git add -A && git commit -m 'Your message'"
    exit 1
fi

# Step 3: Confirm deployment
echo -e "${YELLOW}Ready to deploy branch '$BRANCH' to '$TARGET'${NC}"
read -p "Continue? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo -e "${YELLOW}Step 1: Pushing to origin...${NC}"
git push origin "$BRANCH"

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Push failed. Check git status and try again.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Pushed to origin${NC}"

echo ""
echo -e "${YELLOW}Step 2: Backing up on Raspberry Pi...${NC}"
ssh "$TARGET" "cp -r $REMOTE_PATH $REMOTE_BACKUP_PATH"
echo -e "${GREEN}✓ Backup created at $REMOTE_BACKUP_PATH${NC}"

echo ""
echo -e "${YELLOW}Step 3: Pulling changes on Raspberry Pi...${NC}"
ssh "$TARGET" "cd $REMOTE_PATH && git pull origin $BRANCH"

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Pull failed on Pi. Check git config and try again.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Pulled changes${NC}"

echo ""
echo -e "${YELLOW}Step 4: Restarting FastAPI service...${NC}"
ssh "$TARGET" "sudo systemctl restart playbuoy-api"

echo -e "${GREEN}✓ Service restarted${NC}"

echo ""
echo -e "${YELLOW}Step 5: Verifying health...${NC}"
sleep 2
HEALTH=$(ssh "$TARGET" "curl -s http://localhost:8000/health")

if echo "$HEALTH" | grep -q "true"; then
    echo -e "${GREEN}✓ Health check passed: $HEALTH${NC}"
else
    echo -e "${RED}✗ Health check failed: $HEALTH${NC}"
    echo -e "${YELLOW}Backup location: $REMOTE_BACKUP_PATH${NC}"
    echo "To rollback:"
    echo "  ssh $TARGET 'rm -rf $REMOTE_PATH && mv $REMOTE_BACKUP_PATH $REMOTE_PATH && sudo systemctl restart playbuoy-api'"
    exit 1
fi

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}✓ Deployment Successful${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo "Backup location: $REMOTE_BACKUP_PATH"
echo "API status: $(ssh "$TARGET" "sudo systemctl is-active playbuoy-api")"
echo ""

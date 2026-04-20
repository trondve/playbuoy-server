#!/bin/bash
# cleanup-postgresql.sh
# Remove unused PostgreSQL tables from playbuoy database
# These tables were created but never used by the FastAPI application (which uses SQLite)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}======================================${NC}"
echo -e "${YELLOW}PlayBuoy PostgreSQL Cleanup Script${NC}"
echo -e "${YELLOW}======================================${NC}"
echo ""
echo -e "${RED}WARNING: This script will DELETE the following unused tables:${NC}"
echo "  - buoy_data (orphaned schema, 21 test records)"
echo "  - alert_log (orphaned schema, 0 records)"
echo ""
echo -e "${RED}These tables are NOT used by the FastAPI application.${NC}"
echo "The FastAPI app uses SQLite (playbuoy.db) instead."
echo ""

# Require explicit confirmation
read -p "Type 'yes' to confirm deletion: " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted. No changes made."
    exit 0
fi

echo ""
echo -e "${YELLOW}Step 1: Backing up PostgreSQL database...${NC}"
BACKUP_FILE="/home/playbuoyadmin/playbuoy-backup-$(date +%Y%m%d-%H%M%S).sql"
echo "Backup location: $BACKUP_FILE"

# Backup the entire database using pg_dump
sudo -u postgres pg_dump -U postgres playbuoy > "$BACKUP_FILE" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Backup created successfully${NC}"
else
    echo -e "${RED}✗ Backup failed. Aborting.${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 2: Dropping unused tables...${NC}"

# Drop the tables using psql
sudo -u postgres psql -d playbuoy << EOF
-- Drop the unused tables
DROP TABLE IF EXISTS alert_log CASCADE;
DROP TABLE IF EXISTS buoy_data CASCADE;

-- Drop sequences if they exist
DROP SEQUENCE IF EXISTS alert_log_id_seq CASCADE;
DROP SEQUENCE IF EXISTS buoy_data_id_seq CASCADE;

-- Verify tables are gone
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Tables dropped successfully${NC}"
else
    echo -e "${RED}✗ Table drop failed. Check backup at $BACKUP_FILE${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Step 3: Verifying cleanup...${NC}"

# Count remaining tables
TABLE_COUNT=$(sudo -u postgres psql -d playbuoy -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
echo "Remaining tables in 'playbuoy' database: $TABLE_COUNT"

if [ "$TABLE_COUNT" -eq 0 ]; then
    echo -e "${YELLOW}Note: Database is now empty (no tables). This is expected.${NC}"
    echo -e "${YELLOW}The FastAPI app uses SQLite (playbuoy.db), not PostgreSQL.${NC}"
else
    echo "Remaining tables:"
    sudo -u postgres psql -d playbuoy -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
fi

echo ""
echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}Cleanup Complete${NC}"
echo -e "${GREEN}======================================${NC}"
echo ""
echo "Summary:"
echo "  - Backup saved: $BACKUP_FILE"
echo "  - Unused tables removed"
echo "  - SQLite database (playbuoy.db) is unaffected"
echo ""
echo "To restore from backup (if needed):"
echo "  sudo -u postgres psql playbuoy < $BACKUP_FILE"
echo ""

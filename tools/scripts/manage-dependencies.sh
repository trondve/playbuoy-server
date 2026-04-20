#!/bin/bash
# manage-dependencies.sh
# Helper script to check, update, and manage Python dependencies on Raspberry Pi

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

VENV_PATH="/home/playbuoyadmin/playbuoy-server/venv"
REQ_FILE="/home/playbuoyadmin/playbuoy-server/requirements.txt"

echo -e "${YELLOW}======================================${NC}"
echo -e "${YELLOW}PlayBuoy Dependency Manager${NC}"
echo -e "${YELLOW}======================================${NC}"
echo ""

# Function to activate venv and run command
run_in_venv() {
    source "$VENV_PATH/bin/activate"
    "$@"
}

# Menu
show_menu() {
    echo "Options:"
    echo "  1) Check current versions"
    echo "  2) Check for outdated packages"
    echo "  3) Check for security updates"
    echo "  4) Update specific package"
    echo "  5) Freeze current environment to requirements.txt"
    echo "  6) Install from requirements.txt"
    echo "  7) Show dependency tree"
    echo ""
    read -p "Select option (1-7): " OPTION
}

# Option 1: Check current versions
check_versions() {
    echo -e "${YELLOW}Current installed packages:${NC}"
    run_in_venv pip list
}

# Option 2: Check for outdated
check_outdated() {
    echo -e "${YELLOW}Checking for outdated packages...${NC}"
    echo "(This may take a minute)"
    run_in_venv pip list --outdated
}

# Option 3: Check for security updates
check_security() {
    echo -e "${YELLOW}Checking for security vulnerabilities...${NC}"
    echo "(Requires pip-audit tool)"

    # Try using pip-audit if available
    if run_in_venv pip show pip-audit > /dev/null 2>&1; then
        run_in_venv pip-audit
    else
        echo -e "${YELLOW}Installing pip-audit...${NC}"
        run_in_venv pip install --upgrade pip-audit
        run_in_venv pip-audit
    fi
}

# Option 4: Update specific package
update_package() {
    read -p "Package name to update: " PKG_NAME
    read -p "Version (leave blank for latest): " PKG_VERSION

    if [ -z "$PKG_VERSION" ]; then
        echo -e "${YELLOW}Installing latest version of $PKG_NAME...${NC}"
        run_in_venv pip install --upgrade "$PKG_NAME"
    else
        echo -e "${YELLOW}Installing $PKG_NAME==$PKG_VERSION...${NC}"
        run_in_venv pip install "$PKG_NAME==$PKG_VERSION"
    fi

    echo -e "${GREEN}✓ Update complete${NC}"
    echo ""
    echo "To save changes:"
    echo "  bash $0"
    echo "  (Select option 5)"
}

# Option 5: Freeze requirements
freeze_requirements() {
    echo -e "${YELLOW}Saving current environment to requirements.txt...${NC}"
    run_in_venv pip freeze > "$REQ_FILE"
    echo -e "${GREEN}✓ Saved to $REQ_FILE${NC}"
    echo ""
    echo "New requirements.txt content (first 10 lines):"
    head -10 "$REQ_FILE"
}

# Option 6: Install from requirements
install_requirements() {
    echo -e "${YELLOW}Installing from requirements.txt...${NC}"
    run_in_venv pip install -r "$REQ_FILE"
    echo -e "${GREEN}✓ Installation complete${NC}"
}

# Option 7: Show dependency tree
show_tree() {
    echo -e "${YELLOW}Showing dependency tree...${NC}"

    if run_in_venv pip show pipdeptree > /dev/null 2>&1; then
        run_in_venv pipdeptree
    else
        echo -e "${YELLOW}Installing pipdeptree...${NC}"
        run_in_venv pip install pipdeptree
        run_in_venv pipdeptree
    fi
}

# Main loop
while true; do
    show_menu

    case $OPTION in
        1) check_versions ;;
        2) check_outdated ;;
        3) check_security ;;
        4) update_package ;;
        5) freeze_requirements ;;
        6) install_requirements ;;
        7) show_tree ;;
        *) echo "Invalid option"; exit 1 ;;
    esac

    echo ""
    read -p "Continue? (y/n): " CONTINUE
    if [ "$CONTINUE" != "y" ]; then
        break
    fi
    echo ""
done

echo -e "${GREEN}Done${NC}"

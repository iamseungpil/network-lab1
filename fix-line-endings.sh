#!/bin/bash
# Fix line endings and make scripts executable

echo "🔧 Fixing line endings and setting permissions..."

# Fix line endings
if command -v dos2unix &> /dev/null; then
    echo "Using dos2unix..."
    find . -name "*.sh" -type f -exec dos2unix {} \; 2>/dev/null
else
    echo "Using sed..."
    find . -name "*.sh" -type f -exec sed -i 's/\r$//' {} \; 2>/dev/null
fi

# Make all shell scripts executable
chmod +x *.sh 2>/dev/null
chmod +x docker-scripts/*.sh 2>/dev/null

echo "✅ Done! All scripts are ready to use."
echo ""
echo "📋 Available scripts:"
echo "  ./run-all.sh         - Start everything automatically (recommended)"
echo "  ./run-gitbash.sh     - Git Bash compatible version"
echo "  ./run-background.sh  - Run in background mode"
echo "  ./docker-run.sh      - Create container only"
echo "  ./rebuild.sh         - Rebuild container from scratch"
echo "  ./test-container.sh  - Test container setup"
echo ""
echo "🚀 To start, run: ./run-all.sh"
echo "🔄 If you have issues, run: ./rebuild.sh"

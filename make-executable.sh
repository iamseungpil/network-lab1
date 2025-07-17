#!/bin/bash
# Make all scripts executable

echo "Setting execute permissions for all scripts..."

chmod +x *.sh
chmod +x docker-scripts/*.sh 2>/dev/null || true
chmod +x mininet/*.py

echo "✅ Done! All scripts are now executable."
echo ""
echo "🚀 Quick Start Options:"
echo ""
echo "📝 SIMPLE (Recommended for beginners):"
echo "  ./run-simple.sh           - Start everything at once, connect to screen"
echo ""
echo "📝 ADVANCED (For power users):"
echo "  ./run.sh                  - Start with tmux (dual windows)"
echo "  ./connect.sh              - Reconnect to tmux session"
echo ""
echo "📝 Manual control:"
echo "  ./start_controllers.sh    - Start only RYU controllers"
echo "  ./start_mininet.sh        - Start only Mininet"
echo "  ./start_sdn.sh            - Combined start script (for containers)"
echo ""
echo "📝 Utilities:"
echo "  ./rebuild.sh              - Rebuild container from scratch"
echo "  ./fix-line-endings.sh     - Fix Windows line endings"
echo ""
echo "💡 New users should start with: ./run-simple.sh"
echo "📖 For detailed guide: see TMUX-GUIDE.md"

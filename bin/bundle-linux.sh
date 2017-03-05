#!/bin/sh

# make sure old build is deleted
rm -r obsidian-panel 2>/dev/null
cd ..
rm -r build/ 2>/dev/null
rm -r dist/ 2>/dev/null

echo_bold() {
    echo -e "\033[1m"$1"\033[0m"
}

echo_bold "Start bundling..."

pyinstaller .pyinstall.spec

echo_bold "Make Bundle..."

cd bin
mkdir -p obsidian-panel/bundle
mkdir -p obsidian-panel/binary

mv ../dist/launch/* obsidian-panel/bundle
cp -r linux/ob-panel.sh obsidian-panel/binary
cp -r linux/start-panel.sh obsidian-panel

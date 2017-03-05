#!/bin/sh

# make sure old build is deleted
rm -rf ./bundle-linux/ 2>/dev/null
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
mkdir -p bundle-linux/bundle
mkdir -p bundle-linux/bundle/app
mkdir -p bundle-linux/binary

mv ../dist/launch/* bundle-linux/bundle
cp -r ../app/templates bundle-linux/bundle
cp -r ../app/static bundle-linux/bundle/app

cp -r linux/ob-panel.sh bundle-linux/binary
cp -r linux/start-panel.sh bundle-linux

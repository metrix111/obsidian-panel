#!/bin/sh

BUNDLE_DIR="ob-panel-linux"

# make sure old build is deleted
rm -rf ./$BUNDLE_DIR 2>/dev/null
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
mkdir -p $BUNDLE_DIR/bundle
mkdir -p $BUNDLE_DIR/bundle/app
mkdir -p $BUNDLE_DIR/binary

mv ../dist/launch/* $BUNDLE_DIR/bundle
cp -r ../app/templates $BUNDLE_DIR/bundle
cp -r ../app/static $BUNDLE_DIR/bundle/app

cp -r linux/ob-panel.sh $BUNDLE_DIR/binary
cp -r linux/start-panel.sh $BUNDLE_DIR

echo "[success]"

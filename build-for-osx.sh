mkdir -p build-osx/
pushd build-osx/
cmake -D SCAP_WORKBENCH_LOCAL_SCAN_ENABLED=false -D SCAP_AS_RPM_EXECUTABLE="" ../
make -j 4
mkdir -p ./scap-workbench.app/Contents/Frameworks/
cp /usr/local/lib/libpcre.1.dylib ./scap-workbench.app/Contents/Frameworks/
cp /usr/local/lib/libopenscap.8.dylib ./scap-workbench.app/Contents/Frameworks/
chmod 755 ./scap-workbench.app/Contents/Frameworks/*.dylib
echo "Copy fresh extracted SSG zip into `pwd`/scap-workbench.app/Contents/Resources/ssg/"
echo "so that SSG README.md is at `pwd`/scap-workbench.app/Contents/Resources/ssg/README.md"
echo "Then change directory to `pwd` and run \"sh osx-create-dmg.sh\""
popd

#!/bin/bash
# Build Streamflix .deb package for Linux
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VERSION="1.4.1"
PKG_NAME="streamflix"
PKG_DIR="${PKG_NAME}_${VERSION}_amd64"
BIN_SRC="dist/Streamflix"

if [ ! -f "$BIN_SRC" ]; then
    echo "Error: $BIN_SRC not found. Run build_linux.sh first."
    exit 1
fi

# Create package structure
mkdir -p "${PKG_DIR}/DEBIAN"
mkdir -p "${PKG_DIR}/usr/bin"
mkdir -p "${PKG_DIR}/usr/share/applications"
mkdir -p "${PKG_DIR}/usr/share/icons/hicolor/256x256/apps"
mkdir -p "${PKG_DIR}/usr/share/doc/${PKG_NAME}"

# Copy binary
cp "$BIN_SRC" "${PKG_DIR}/usr/bin/streamflix"
chmod 755 "${PKG_DIR}/usr/bin/streamflix"

# Create desktop entry
cat > "${PKG_DIR}/usr/share/applications/streamflix.desktop" << 'DESKTOP'
[Desktop Entry]
Name=Streamflix
Comment=Streaming aggregator - TV, movies, series, IPTV
Exec=/usr/bin/streamflix
Icon=streamflix
Terminal=false
Type=Application
Categories=AudioVideo;Network;
StartupNotify=true
DESKTOP

# Create simple SVG icon (text-based)
cat > "${PKG_DIR}/usr/share/icons/hicolor/256x256/apps/streamflix.png" << 'ICONEOF'
SKIP
ICONEOF
# Generate a simple PNG icon using Python
python3 -c "
from PIL import Image, ImageDraw, ImageFont
import struct
img = Image.new('RGBA', (256, 256), (20, 20, 30, 255))
draw = ImageDraw.Draw(img)
draw.ellipse([40, 40, 216, 216], fill=(255, 50, 50, 255))
draw.ellipse([60, 60, 196, 196], fill=(0, 0, 0, 0))
draw.text((80, 100), '🎬', fill='white', font_size=80)
draw.text((70, 170), 'SF', fill='white', font_size=40)
img.save('${PKG_DIR}/usr/share/icons/hicolor/256x256/apps/streamflix.png', 'PNG')
" 2>/dev/null || true

# Copy docs
cat > "${PKG_DIR}/usr/share/doc/${PKG_NAME}/README" << 'README'
Streamflix - Streaming aggregator

Access movies, series, IPTV and live TV from multiple Spanish-language providers
in a single desktop application.

Run: streamflix
Fullscreen: streamflix --fullscreen
README

gzip -9 -n "${PKG_DIR}/usr/share/doc/${PKG_NAME}/README"

# Create control file
cat > "${PKG_DIR}/DEBIAN/control" << CONTROL
Package: streamflix
Version: ${VERSION}
Section: video
Priority: optional
Architecture: amd64
Depends: libgtk-3-0 (>= 3.24), libwebkit2gtk-4.1-0 (>= 2.40), gir1.2-webkit2-4.1 (>= 2.40), python3-gi (>= 3.50)
Maintainer: Richiestone18
Description: Streaming aggregator desktop app
 Access movies, series, IPTV and live TV from multiple
 Spanish-language providers in a single desktop application.
 .
 Features:
  - 21 providers: CineCalidad, Pelisplusto, FlixLatam, SoloLatino,
    LatinAnime, LaCartoons, JKanime, IPTV, CableVisionHD, Doramasflix,
    PelisflixHD, MAGISTV, SeriesFlix, TvporinternetHD, TvLibrefutbol,
    PlutoTV MX/AR, AnimeFLV, Animefenix, Latanime
  - HLS proxy backend for IPTV streams (bypasses CORS/mixed-content)
  - Aspect ratio selector (fill, 16:9, 4:3, original)
  - Fullscreen mode
  - HLS.js for IPTV streams
  - No black bars in fill mode
CONTROL

# Build .deb package
dpkg-deb --build -Zxz --root-owner-group "${PKG_DIR}"

# Also create a combined script that builds and uploads
cat > "${PKG_DIR}/DEBIAN/postinst" << 'POSTINST'
#!/bin/sh
set -e
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f /usr/share/icons/hicolor/ || true
fi
POSTINST
chmod 755 "${PKG_DIR}/DEBIAN/postinst"
dpkg-deb --build -Zxz --root-owner-group "${PKG_DIR}"

echo ""
echo "=== Package built ==="
ls -lh "${PKG_DIR}.deb"
echo "Install: sudo dpkg -i ${PKG_DIR}.deb"
echo "Run: streamflix"
echo "Fullscreen: streamflix --fullscreen"
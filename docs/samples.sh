#!/bin/sh
# Rebuild the README samples from the sample reports in assets/: a PDF of each report
# and a preview of its first page. Needs macOS and Google Chrome: sh docs/samples.sh
set -e
cd "$(dirname "$0")/.."
CHROME=${CHROME:-"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"}
tmp=$(mktemp -d)
cp assets/reference-report.html "$tmp/site-report.html"
python3 scripts/build_report.py scaffold --mode portfolio --out "$tmp/portfolio.html" >/dev/null
for name in site-report portfolio; do
  "$CHROME" --headless=new --no-pdf-header-footer --virtual-time-budget=8000 \
    --print-to-pdf="docs/$name.pdf" "file://$tmp/$name.html" 2>/dev/null
  qlmanage -t -s 1000 -o "$tmp" "docs/$name.pdf" >/dev/null
  mv "$tmp/$name.pdf.png" "docs/$name.png"
done
rm -rf "$tmp"

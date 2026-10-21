Mass Exporter Export Lab - offline app

Windows:      double-click "Start Export Lab.bat"
macOS/Linux:  sh start.sh

The page opens at http://localhost:8791/ . It needs no internet connection: three.js is in
vendor/, every exported file of every case is in blobs/. Keep the console window open while
you use the page; close it to stop the server.

Opening index.html directly (file://) does not work - browsers refuse to run its modules
from disk.

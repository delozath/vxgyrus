
from vxgyrus.presentation.cli_viewer import SceneViewer

"""Main entry point for the GUI application.

Put here:
- CLI parsing (optional) or Hydra bootstrap (optional)
- Qt application initialization
- MainWindow creation/show
- graceful shutdown / logging init
"""

from vxgyrus.infrastructure.io.images_2d import JPEGFileHandler

def main() -> int:
    pfname = "file.jpg"
    
    reader = JPEGFileHandler(pfname)
    viewer = SceneViewer(reader.build())
    viewer.start()
    



if __name__ == "__main__":
    main()

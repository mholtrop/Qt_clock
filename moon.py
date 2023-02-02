#!/usr/bin/env python3
#
#
# From NASA website:
#               https://svs.gsfc.nasa.gov/4874  (2021)
#               https://svs.gsfc.nasa.gov/5048  (2023)
#
# /*
# const moon_domain = "https://svs.gsfc.nasa.gov";
# const moon_path = "/vis/a000000/a004800/a004874/";
# const moon_year = 2021;
# const moon_febdays = 28;
# const moon_nimages = 8760;
#

# ======================================================================
# get_moon_imagenum()
#
# Initialize the frame number.  If the current date is within the year
# moon_year, the frame number is the (rounded) number of hours since the
# start of the year.  Otherwise it's 1.
# ====================================================================== */
#
# function get_moon_imagenum()
# {
#    var now = new Date();
#    var year = now.getUTCFullYear();
#    if ( year != moon_year ) {
#       moon_imagenum = 1;
#       return false;
#    }
#    var janone = Date.UTC( year, 0, 1, 0, 0, 0 );
#    moon_imagenum = 1 + Math.round(( now.getTime() - janone ) / 3600000.0 );
#    if ( moon_imagenum > moon_nimages ) moon_imagenum = moon_nimages;
#    return false;
# }
#
# Get moon images locally with:
# cd moon
# wget -nc -w 1 -nd -r  https://svs.gsfc.nasa.gov/vis/a000000/a004800/a004874/frames/216x216_1x1_30p
#

from datetime import datetime

from PySide2.QtWidgets import QApplication, QWidget, QLabel
from PySide2.QtGui import QPixmap, QImage
from PySide2.QtCore import Qt, QFile, Slot, QTimer, QRect
import requests


class QMoon(QWidget):
    """Small widget displays today's moon."""

    def __init__(self, pos=(0, 0), parent=None, size=216, web=False, save=False, debug=0):
        super(QMoon, self).__init__(parent)
        self.total_images = 8760
        self.moon_domain = "https://svs.gsfc.nasa.gov"
        self.moon_path_2021 = "/vis/a000000/a004800/a004874/"
        # https://svs.gsfc.nasa.gov/vis/a000000/a004900/a004955/frames/216x216_1x1_30p/moon.8597.jpg
        self.moon_path = "/vis/a000000/a005000/a005048/"  # 2022: "/vis/a000000/a004900/a004955/"
        self.debug = debug
        self.size = size
        self.get_from_web = web
        self.save = save
        # self.setGeometry(pos[0], pos[1], self.size, self.size)
        self.moon = QLabel(self)
        self.moon.setGeometry(pos[0], pos[1], self.size, self.size)
        self.update()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(3600*1000)
        self.image = None
        self.pixmap = None
        self.moon_image_number = 1

    @Slot()
    def update(self):
        if self.debug > 0:
            print("Updating the Moon Phase pixmap.")
        self.pixmap = self.get_moon_image()
        self.moon.setPixmap(self.pixmap)

    def get_moon_image_number(self):
        #
        # Conversion from the jscript.
        #
        now = datetime.utcnow()
        janone = datetime(now.year, 1, 1, 0, 0, 0)
        self.moon_image_number = round((datetime.utcnow() - janone).total_seconds() / 3600)
        return self.moon_image_number <= self.total_images

    def get_moon_image(self):

        if not self.get_moon_image_number():
            print("Could not get the moon. Are we in a new year?")

        if self.debug:
            print(f"We are using moon image number: {self.moon_image_number}")
        if self.size > 500 or self.get_from_web:

            if self.size > 2160:
                url = self.moon_domain+self.moon_path+"/frames/5760x3240_16x9_30p/" \
                      f"plain/moon.{self.moon_image_number:04d}.tif"
            elif self.size > 216:
                url = self.moon_domain+self.moon_path+"/frames/3840x2160_16x9_30p/" \
                  f"plain/moon.{self.moon_image_number:04d}.tif"
            else:
                url = self.moon_domain + self.moon_path + "/frames/216x216_1x1_30p/" \
                                                      f"moon.{self.moon_image_number:04d}.jpg"

            if self.debug:
                print(f"Getting image from url: {url}")
            req = requests.get(url)
            self.image = QImage()
            self.image.loadFromData(req.content, "tiff")
            size = self.image.size()
            if self.debug:
                print("Image size: ", size)
            if self.save:
                self.image.save(f"moon/moon.{self.moon_image_number:04d}.tiff")

            offset = (size.width() - size.height())/2
            rect = QRect(offset, 0, size.height(), size.height())
            self.image = self.image.copy(rect)
            pix = QPixmap.fromImage(self.image)
            pix = pix.scaled(self.size, self.size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            return pix
        else:
            moon_file = f"moon/moon.{self.moon_image_number:04d}.jpg"
            pix = QPixmap(moon_file)
            pix = pix.scaled(self.size, self.size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            return pix


if __name__ == '__main__':
    import sys
    import argparse
    import signal

    # Call this function in your main after creating the QApplication
    def setup_interrupt_handling():
        """Setup handling of KeyboardInterrupt (Ctrl-C) for PyQt."""
        signal.signal(signal.SIGINT, _interrupt_handler)
        # Regularly run some (any) python code, so the signal handler gets a
        # chance to be executed:
        # safe_timer(50, lambda: None)

    # Define this as a global function to make sure it is not garbage
    # collected when going out of scope:
    def _interrupt_handler(signum, frame):
        """Handle KeyboardInterrupt: quit application."""
        print("You interrupted me with a control-C. ")
        QApplication.quit()


    setup_interrupt_handling()

    app = QApplication(sys.argv)

    parser = argparse.ArgumentParser("Qt based Clock program for Raspberry Pi")
    parser.add_argument("--debug", "-d", action="count", help="Increase debug level.", default=0)
    parser.add_argument("--style", "-S", type=str, help="Use specified style sheet.", default=None)
    parser.add_argument("--frameless", "-fl", action="store_true", help="Make a frameless window.")
    parser.add_argument("--size", "-s", type=int, help="Size of the image to display", default=216)
    parser.add_argument("--web", "-w", action="store_true", help="Get from web even if smaller than 500.")
    parser.add_argument("--save", "-sa", action="store_true", help="Save to file.")

    args = parser.parse_args(sys.argv[1:])

    file = None
    if args.style is None:
        file = QFile("Clock.qss")
    else:
        file = QFile(args.style)

    file.open(QFile.ReadOnly)
    style_sheet = file.readAll()
    # print(style_sheet.data().decode("utf-8"))
    app.setStyleSheet(style_sheet.data().decode("utf-8"))

    moon = QMoon(size=args.size, debug=args.debug, save=True)
    moon.show()
    sys.exit(app.exec_())

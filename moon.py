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
# wget -nc -w 1 -nd -r  https://svs.gsfc.nasa.gov/vis/a000000/a005100/a005187/frames/216x216_1x1_30p

from datetime import datetime
import dateutil.parser as datparser

from PySide2.QtWidgets import QApplication, QWidget, QLabel
from PySide2.QtGui import QPixmap, QImage
from PySide2.QtCore import Qt, QFile, Slot, QTimer, QRect
import requests
import os


class QMoon(QWidget):
    """Small widget displays today's moon."""

    def __init__(self, pos=(0, 0), parent=None, date=None, size=216, web=False, save=False, debug=0):
        super(QMoon, self).__init__(parent)
        self.total_images = 8760
        self.moon_domain = "https://svs.gsfc.nasa.gov" # "https://svs.gsfc.nasa.gov"
        self.moon_path_2021 = "/vis/a000000/a004800/a004874/"
        self.moon_path_2022 = "/vis/a000000/a004900/a004955/"
        self.moon_path_2023 = "/vis/a000000/a005000/a005048/"
        self.moon_path_2024 = "/vis/a000000/a005100/a005187/"
        self.moon_path_2025 = "/vis/a000000/a005400/a005415/"
        # https://svs.gsfc.nasa.gov/vis/a000000/a004900/a004955/frames/216x216_1x1_30p/moon.8597.jpg
        self.moon_path = "/vis/a000000/a005400/a005415/"   #
        self.debug = debug
        self.size = size
        self.get_from_web = web
        self.save = save
        # self.setGeometry(pos[0], pos[1], self.size, self.size)
        self.date = date
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
        if self.date is None:
            now = datetime.utcnow()
        else:
            now = self.date
        if self.debug:
            print(f"Using date: {now}")
        janone = datetime(now.year, 1, 1, 0, 0, 0)
        self.moon_image_number = round((now - janone).total_seconds() / 3600)
        if self.debug:
            print(f"Moon_image_number: {self.moon_image_number}")
        return self.moon_image_number <= self.total_images

    def get_moon_image(self):

        if not self.get_moon_image_number():
            print("Could not get the moon. Are we in a new year?")

        moon_file = f"moon/moon.{self.moon_image_number:04d}.jpg"
        if not os.path.exists(moon_file):
            self.get_from_web = True

        if self.debug:
            print(f"We are using moon image number: {self.moon_image_number}")
        if self.size > 500 or self.get_from_web:

            extension = "tif"
            if self.size > 2160:
                url = self.moon_domain+self.moon_path+"/frames/5760x3240_16x9_30p/" \
                      f"plain/moon.{self.moon_image_number:04d}.tif"
            elif self.size > 216:
                url = self.moon_domain+self.moon_path+"/frames/3840x2160_16x9_30p/" \
                  f"plain/moon.{self.moon_image_number:04d}.tif"
            else:
                url = self.moon_domain + self.moon_path + "/frames/216x216_1x1_30p/" \
                                                      f"moon.{self.moon_image_number:04d}.jpg"
                extension = "jpg"

            if self.debug:
                print(f"Getting image from url: {url}")
            req = requests.get(url)
            if self.debug:
                print(f"Request status code: {req.status_code}")
            self.image = QImage()
            self.image.loadFromData(req.content, extension)
            size = self.image.size()
            if self.debug:
                print("Image size: ", size)
            if self.save:
                self.image.save(f"moon/moon.{self.moon_image_number:04d}.{extension}")

            offset = (size.width() - size.height())/2
            rect = QRect(offset, 0, size.height(), size.height())
            self.image = self.image.copy(rect)
            pix = QPixmap.fromImage(self.image)
            pix = pix.scaled(self.size, self.size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            return pix
        else:

            pix = QPixmap(moon_file)
            pix = pix.scaled(self.size, self.size, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            return pix


def main():
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
    parser.add_argument("--date", "-D", type=str, help="Use specified date.", default=None)
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

    if args.date is not None:
        date_check = datparser.parse(args.date)
        if args.debug > 0:
            print("Date to use: ", date_check)
    else:
        date_check = None


    moon = QMoon(size=args.size, date=date_check, debug=args.debug, web=args.web, save=True)
    moon.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

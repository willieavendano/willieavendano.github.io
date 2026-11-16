"""One-motor Silly Walks starter for VEXcode V5 Python.

Paste into a new Python project with no motors added in Devices.
This file configures the motor itself: port 1, green 18:1 cartridge.
For a red cartridge use RATIO_36_1; for blue use RATIO_6_1.
Requires a physical V5 Brain; desktop Python cannot run the vex module.
"""

from vex import *

walk_motor = Motor(Ports.PORT1, GearSetting.RATIO_18_1, False)

SPEED_PERCENT = 25
RUN_SECONDS = 5


def main():
    # Continuous rotation suits a crank-driven walking mechanism.
    # Change FORWARD to REVERSE if the mechanism travels backward.
    try:
        walk_motor.spin(FORWARD, SPEED_PERCENT, PERCENT)
        wait(RUN_SECONDS, SECONDS)
    finally:
        walk_motor.stop(BRAKE)


main()

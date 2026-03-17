# Copyright (C) 2024 - 2026, IDS Imaging Development Systems GmbH.
#
# Permission to use, copy, modify, and/or distribute this software for
# any purpose with or without fee is hereby granted.
#
# THE SOFTWARE IS PROVIDED “AS IS” AND THE AUTHOR DISCLAIMS ALL
# WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES
# OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE
# FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN
# AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT
# OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""
This example shows how to display a live camera image using
pyside6 and QtWidgets.
"""

from __future__ import annotations

import sys
import signal
from types import FrameType
from typing import cast, Optional

from PySide6.QtWidgets import QApplication

from mainwindow import MainWindow


def main() -> int:
    a = QApplication(sys.argv)
    w = MainWindow()
    w.show()

    def handle_sigint(signum: int, frame: Optional[FrameType]) -> None:
        a.quit()

    signal.signal(signal.SIGINT, handle_sigint)

    try:
        return cast(int, a.exec())
    except AttributeError:
        return cast(int, a.exec_())


if __name__ == "__main__":
    sys.exit(main())

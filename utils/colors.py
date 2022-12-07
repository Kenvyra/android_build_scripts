# Vendored from "ansicolors" by Giorgos Verigakis and heavily modified by us
# to use an enum-based API
#
# Copyright (c) 2012 Giorgos Verigakis <verigak@gmail.com>
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
from enum import Enum
from functools import partial


class Color(Enum):
    BLACK = 0
    RED = 1
    GREEN = 2
    YELLOW = 3
    BLUE = 4
    MAGENTA = 5
    CYAN = 6
    WHITE = 7


class Style(Enum):
    BOLD = 0
    FAINT = 1
    ITALIC = 2
    UNDERLINE = 3
    BLINK = 4
    BLINK2 = 5
    NEGATIVE = 6
    CONCEALED = 7
    CROSSED = 8


def color(
    s: str,
    fg: Color | None = None,
    bg: Color | None = None,
    style: Style | list[Style] = [],
):
    sgr = []

    if fg:
        sgr.append(f"{30 + fg.value}")

    if bg:
        sgr.append(f"{40 + bg.value}")

    if isinstance(style, list):
        for st in style:
            sgr.append(f"{1 + st.value}")
    else:
        sgr.append(f"{1 + style.value}")

    if sgr:
        prefix = f"\x1b[{';'.join(sgr)}m"
        suffix = "\x1b[0m"
        return f"{prefix}{s}{suffix}"
    else:
        return s


# Foreground shortcuts
black = partial(color, fg=Color.BLACK)
red = partial(color, fg=Color.RED)
green = partial(color, fg=Color.GREEN)
yellow = partial(color, fg=Color.YELLOW)
blue = partial(color, fg=Color.BLUE)
magenta = partial(color, fg=Color.MAGENTA)
cyan = partial(color, fg=Color.CYAN)
white = partial(color, fg=Color.WHITE)

# Style shortcuts
bold = partial(color, style=Style.BOLD)
faint = partial(color, style=Style.FAINT)
italic = partial(color, style=Style.ITALIC)
underline = partial(color, style=Style.UNDERLINE)
blink = partial(color, style=Style.BLINK)
blink2 = partial(color, style=Style.BLINK2)
negative = partial(color, style=Style.NEGATIVE)
concealed = partial(color, style=Style.CONCEALED)
crossed = partial(color, style=Style.CROSSED)

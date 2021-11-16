import logging
logger = logging.getLogger(__name__)
from re import compile as re_compile

__Ha = [[0x2E80, 0x2E99],    # Han # So  [26] CJK RADICAL REPEAT, CJK RADICAL RAP
        [0x2E9B, 0x2EF3],    # Han # So  [89] CJK RADICAL CHOKE, CJK RADICAL C-SIMPLIFIED TURTLE
        [0x2F00, 0x2FD5],    # Han # So [214] KANGXI RADICAL ONE, KANGXI RADICAL FLUTE
        0x3005,              # Han # Lm       IDEOGRAPHIC ITERATION MARK
        0x3007,              # Han # Nl       IDEOGRAPHIC NUMBER ZERO
        [0x3021, 0x3029],    # Han # Nl   [9] HANGZHOU NUMERAL ONE, HANGZHOU NUMERAL NINE
        [0x3038, 0x303A],    # Han # Nl   [3] HANGZHOU NUMERAL TEN, HANGZHOU NUMERAL THIRTY
        0x303B,              # Han # Lm       VERTICAL IDEOGRAPHIC ITERATION MARK
        [0x3400, 0x4DB5],    # Han # Lo [6582] CJK UNIFIED IDEOGRAPH-3400, CJK UNIFIED IDEOGRAPH-4DB5
        [0x4E00, 0x9FC3],    # Han # Lo [20932] CJK UNIFIED IDEOGRAPH-4E00, CJK UNIFIED IDEOGRAPH-9FC3
        [0xF900, 0xFA2D],    # Han # Lo [302] CJK COMPATIBILITY IDEOGRAPH-F900, CJK COMPATIBILITY IDEOGRAPH-FA2D
        [0xFA30, 0xFA6A],    # Han # Lo  [59] CJK COMPATIBILITY IDEOGRAPH-FA30, CJK COMPATIBILITY IDEOGRAPH-FA6A
        [0xFA70, 0xFAD9],    # Han # Lo [106] CJK COMPATIBILITY IDEOGRAPH-FA70, CJK COMPATIBILITY IDEOGRAPH-FAD9
        [0x20000, 0x2A6D6],  # Han # Lo [42711] CJK UNIFIED IDEOGRAPH-20000, CJK UNIFIED IDEOGRAPH-2A6D6
        [0x2F800, 0x2FA1D],  # Han # Lo [542] CJK COMPATIBILITY IDEOGRAPH-2F800, CJK COMPATIBILITY IDEOGRAPH-2FA1D
        [0xFF00, 0xFFEF]]    # Halfwidth and Fullwidth Forms - added
def __build_re():
    # https://stackoverflow.com/questions/34587346/python-check-if-a-string-contains-chinese-character/34587468
    L = []
    for i in __Ha:
        if isinstance(i, list):
            f, t = i
            try:
                f = chr(f)
                t = chr(t)
                L.append(f'{f}-{t}')
            except Exception:
                logger.exception("__build_re")
                # A narrow python build, so can't use chars > 65535 without surrogate pairs!
        else:
            try:
                L.append(chr(i))
            except Exception:
                logger.exception("__build_re")

    RE = f"[{''.join(L)}]"
    return re_compile(RE)

_CJKRE = __build_re()

def find_cjk_letters(text: str) -> list:
    return _CJKRE.findall(text)

from io import DEFAULT_BUFFER_SIZE
def back_readline_b(fp):
    pos = fp.seek(0, 2)
    if pos == 0:
        return
    previous = b''
    while pos > 0:
        next = max(pos - DEFAULT_BUFFER_SIZE, 0)
        fp.seek(next)
        got = fp.read(pos - next)
        got = got + previous
        blines = got.split(b'\n')
        while len(blines) > 1:
            yield blines.pop(-1)
        previous = blines[0]
        pos = next
    yield blines.pop(-1)

def back_readline(fp):
    for l in back_readline_b(fp):
        yield l.decode("utf-8")

def back_readline_s(fp):
    size_sum = 0
    for l in back_readline_b(fp):
        size_sum += len(l) + 1
        yield (l.decode("utf-8"), -max(0, size_sum-1))

def back_readline_s_lastline(fp):
    size_sum = 0
    for l in back_readline_b(fp):
        _i = (l.decode("utf-8"), -max(0, size_sum-1))
        size_sum += len(l) + 1
        yield _i

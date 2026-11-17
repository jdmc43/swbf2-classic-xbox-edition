"""Tiny Windows screen tool (no dependencies).

  screen.py shot <out.png> [scale]      capture primary screen (scale=2 halves size)
  screen.py key <name> [count]          tap a key via scancode (up/down/left/right/enter/esc/space/tab/...)
  screen.py click <x> <y>               left click at absolute screen coords
  screen.py move <x> <y>
  screen.py windows                     list visible top-level windows
"""
import ctypes
import struct
import sys
import time
import zlib
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
user32.SetProcessDPIAware()


def shot(path, scale=1, region=None):
    w, h = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    ox, oy = 0, 0
    if region:
        ox, oy, w, h = region
    hdc = user32.GetDC(0)
    mdc = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    gdi32.SelectObject(mdc, bmp)
    gdi32.BitBlt(mdc, 0, 0, w, h, hdc, ox, oy, 0x00CC0020 | 0x40000000)  # SRCCOPY|CAPTUREBLT

    class BIH(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                    ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                    ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                    ("biClrImportant", wintypes.DWORD)]

    bih = BIH(ctypes.sizeof(BIH), w, -h, 1, 32, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bih), 0)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(mdc)
    user32.ReleaseDC(0, hdc)

    raw = bytearray()
    data = memoryview(buf.raw)
    ow = (w + scale - 1) // scale
    for y in range(0, h, scale):
        row = data[y * w * 4:(y + 1) * w * 4].cast("I")[::scale].tobytes()
        b = bytearray(row)
        b[0::4], b[2::4] = b[2::4], b[0::4]  # BGRA -> RGBA
        raw += b"\0" + bytes(b)
    oh = (h + scale - 1) // scale

    def png_chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", struct.pack(">IIBBBBB", ow, oh, 8, 6, 0, 0, 0))
    png += png_chunk(b"IDAT", zlib.compress(bytes(raw), 6)) + png_chunk(b"IEND", b"")
    open(path, "wb").write(png)
    print(f"saved {path} ({ow}x{oh} from {w}x{h})")


SC = {"esc": 0x01, "enter": 0x1C, "space": 0x39, "tab": 0x0F, "backspace": 0x0E,
      "up": (0x48, True), "down": (0x50, True), "left": (0x4B, True), "right": (0x4D, True),
      "pgup": (0x49, True), "pgdn": (0x51, True), "f1": 0x3B, "f2": 0x3C, "1": 0x02, "2": 0x03, "f10": 0x44,
      "1": 0x02, "2": 0x03, "3": 0x04, "4": 0x05, "5": 0x06, "6": 0x07, "7": 0x08, "8": 0x09, "9": 0x0A, "0": 0x0B, "del": (0x53, True), "end": (0x4F, True), "home": (0x47, True),
      "a": 0x1E, "d": 0x20, "s": 0x1F, "w": 0x11, "e": 0x12, "q": 0x10, "r": 0x13, "c": 0x2E, "g": 0x22, "f": 0x21, "h": 0x23, "j": 0x24, "alt": 0x38, "f4": 0x3E, "f3": 0x3D, "f1": 0x3B, "f2": 0x3C, "1": 0x02, "2": 0x03, "m": 0x32, "x": 0x2D, "z": 0x2C, "t": 0x14, "y": 0x15}


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]


class _U(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("pad", ctypes.c_byte * 32)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _U)]


def send(inp):
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))


def key(name, count=1):
    sc = SC[name]
    ext = False
    if isinstance(sc, tuple):
        sc, ext = sc
    for _ in range(count):
        for up in (False, True):
            flags = 0x0008 | (0x0001 if ext else 0) | (0x0002 if up else 0)  # SCANCODE|EXTENDED|KEYUP
            send(INPUT(1, _U(ki=KEYBDINPUT(0, sc, flags, 0, 0))))
            time.sleep(0.08)
        time.sleep(0.25)


def move(x, y):
    w, h = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    send(INPUT(0, _U(mi=MOUSEINPUT(int(x * 65535 / (w - 1)), int(y * 65535 / (h - 1)), 0, 0x8001, 0, 0))))


def click(x, y):
    move(x, y)
    time.sleep(0.15)
    for f in (0x0002, 0x0004):
        send(INPUT(0, _U(mi=MOUSEINPUT(0, 0, 0, f, 0, 0))))
        time.sleep(0.08)


def rmove(dx, dy, steps=20):
    for i in range(steps):
        sx = dx * (i + 1) // steps - dx * i // steps
        sy = dy * (i + 1) // steps - dy * i // steps
        send(INPUT(0, _U(mi=MOUSEINPUT(sx, sy, 0, 0x0001, 0, 0))))
        time.sleep(0.02)


def lclick():
    for f in (0x0002, 0x0004):
        send(INPUT(0, _U(mi=MOUSEINPUT(0, 0, 0, f, 0, 0))))
        time.sleep(0.1)


def windows():
    cb = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def f(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            n = user32.GetWindowTextLengthW(hwnd)
            if n:
                b = ctypes.create_unicode_buffer(n + 1)
                user32.GetWindowTextW(hwnd, b, n + 1)
                r = wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(r))
                print(hwnd, repr(b.value), (r.left, r.top, r.right, r.bottom))
        return True

    user32.EnumWindows(cb(f), 0)


def focus(sub):
    cb = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    found = []

    def f(hwnd, _):
        n = user32.GetWindowTextLengthW(hwnd)
        if n and user32.IsWindowVisible(hwnd):
            b = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, b, n + 1)
            if sub.lower() in b.value.lower():
                found.append((hwnd, b.value))
        return True

    user32.EnumWindows(cb(f), 0)
    if not found:
        print("no window matching", sub)
        return
    hwnd, title = found[0]
    if user32.GetForegroundWindow() == hwnd:
        print("already focused", hwnd, repr(title))
        return
    # attach to the current foreground thread so SetForegroundWindow is allowed (no keystrokes)
    kernel32 = ctypes.WinDLL("kernel32")
    fg = user32.GetForegroundWindow()
    fg_thread = user32.GetWindowThreadProcessId(fg, None)
    me = kernel32.GetCurrentThreadId()
    user32.AttachThreadInput(me, fg_thread, True)
    user32.ShowWindow(hwnd, 9)
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)
    user32.AttachThreadInput(me, fg_thread, False)
    print("focused", hwnd, repr(title))


def wclick(sub, x, y):
    """Focus the window whose title contains `sub`, then click (x, y) only if that point belongs
    to that window (refuses to click anything else)."""
    focus(sub)
    time.sleep(0.4)
    pt = wintypes.POINT(x, y)
    hit = user32.WindowFromPoint(pt)
    root = user32.GetAncestor(hit, 2)  # GA_ROOT
    n = user32.GetWindowTextLengthW(root)
    b = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(root, b, n + 1)
    fg = user32.GetForegroundWindow()
    if sub.lower() not in b.value.lower() or root != fg:
        print("REFUSED: point belongs to", repr(b.value), "(foreground ok:", root == fg, ")")
        return False
    click(x, y)
    print("clicked", (x, y), "in", repr(b.value))
    return True


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "wclick":
        wclick(sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
    elif cmd == "focus":
        focus(sys.argv[2])
    if cmd == "shot":
        shot(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 1,
             tuple(map(int, sys.argv[4:8])) if len(sys.argv) > 7 else None)
    elif cmd == "key":
        key(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 1)
    elif cmd == "click":
        click(int(sys.argv[2]), int(sys.argv[3]))
    elif cmd == "rmove":
        rmove(int(sys.argv[2]), int(sys.argv[3]))
    elif cmd == "lclick":
        lclick()
    elif cmd == "move":
        move(int(sys.argv[2]), int(sys.argv[3]))
    elif cmd == "windows":
        windows()


def chord(names):
    """press several keys together (like Steam Input does for one button), then release in reverse"""
    keys = []
    for n in names:
        sc = SC[n]; ext = False
        if isinstance(sc, tuple):
            sc, ext = sc
        keys.append((sc, ext))
    for sc, ext in keys:
        send(INPUT(1, _U(ki=KEYBDINPUT(0, sc, 0x0008 | (0x0001 if ext else 0), 0, 0))))
        time.sleep(0.02)
    time.sleep(0.1)
    for sc, ext in reversed(keys):
        send(INPUT(1, _U(ki=KEYBDINPUT(0, sc, 0x0008 | (0x0001 if ext else 0) | 0x0002, 0, 0))))
        time.sleep(0.02)
    time.sleep(0.3)

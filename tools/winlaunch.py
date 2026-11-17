"""Launch SWBF2 windowed on the second monitor without disturbing the foreground app.
usage: winlaunch.py launch             start via Steam (-applaunch 6060 /win -resolution 1920 1080), move window, give focus back
       winlaunch.py move               move an existing SWBF2 window to monitor 2, topmost, without activating it
       winlaunch.py shot <png> [scale] capture the SWBF2 window's own content (PrintWindow, DPI/position independent)
       winlaunch.py alive              exit 0 if the SWBF2 window exists
       winlaunch.py fg                 print the foreground window handle
       winlaunch.py focus <hwnd>       give focus back to a window
"""
import ctypes, struct, subprocess, sys, time, zlib
from ctypes import wintypes

u = ctypes.windll.user32
k = ctypes.windll.kernel32
g = ctypes.windll.gdi32
# per-monitor DPI awareness (monitor 2 has a different scale than the primary)
try:
    u.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except Exception:
    u.SetProcessDPIAware()
TITLE = "Star Wars Battlefront II"
STEAM = r"C:\Program Files (x86)\Steam\steam.exe"


def game():
    return u.FindWindowW(None, TITLE)


def monitor2():
    mons = []
    CB = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)

    class MI(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT), ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]

    def f(h, dc, r, l):
        mi = MI(); mi.cbSize = ctypes.sizeof(MI); u.GetMonitorInfoW(h, ctypes.byref(mi))
        if not mi.dwFlags & 1:
            w = mi.rcWork; mons.append((w.left, w.top, w.right, w.bottom))
        return True
    u.EnumDisplayMonitors(None, None, CB(f), 0)
    return mons[0] if mons else None


def give_focus(hwnd):
    if not hwnd or not u.IsWindow(hwnd):
        return
    fg = u.GetForegroundWindow()
    t1 = u.GetWindowThreadProcessId(fg, None)
    me = k.GetCurrentThreadId()
    u.AttachThreadInput(me, t1, True)
    u.SetForegroundWindow(hwnd)
    u.AttachThreadInput(me, t1, False)


def move():
    h = game()
    m = monitor2()
    if not h or not m:
        return False
    SWP_NOSIZE, SWP_NOACTIVATE = 0x1, 0x10
    HWND_TOPMOST = wintypes.HWND(-1)
    # top-left of monitor 2: on top of other windows there, but not focused
    u.SetWindowPos(h, HWND_TOPMOST, m[0], m[1], 0, 0, SWP_NOSIZE | SWP_NOACTIVATE)
    return True


class BIH(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG), ("biHeight", wintypes.LONG),
                ("biPlanes", wintypes.WORD), ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG), ("biYPelsPerMeter", wintypes.LONG),
                ("biClrUsed", wintypes.DWORD), ("biClrImportant", wintypes.DWORD)]


def shot(path, sc=1):
    h = game()
    r = wintypes.RECT(); u.GetClientRect(h, ctypes.byref(r))
    w, hh = r.right, r.bottom
    hdc = u.GetDC(h); mdc = g.CreateCompatibleDC(hdc); bmp = g.CreateCompatibleBitmap(hdc, w, hh)
    g.SelectObject(mdc, bmp)
    u.PrintWindow(h, mdc, 3)  # PW_CLIENTONLY | PW_RENDERFULLCONTENT
    bih = BIH(ctypes.sizeof(BIH), w, -hh, 1, 32, 0, 0, 0, 0, 0, 0)
    buf = ctypes.create_string_buffer(w * hh * 4)
    g.GetDIBits(mdc, bmp, 0, hh, buf, ctypes.byref(bih), 0)
    g.DeleteObject(bmp); g.DeleteDC(mdc); u.ReleaseDC(h, hdc)
    raw = buf.raw
    ow, oh = w // sc, hh // sc
    out = bytearray()
    for yy in range(oh):
        out.append(0)
        row = (yy * sc) * w * 4
        for xx in range(ow):
            i = row + xx * sc * 4
            out += bytes((raw[i + 2], raw[i + 1], raw[i], 255))

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    png = bytes([0x89]) + b"PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", ow, oh, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(out), 6)) + chunk(b"IEND", b"")
    open(path, "wb").write(png)
    print("saved %s (%dx%d client)" % (path, w, hh))


cmd = sys.argv[1]
if cmd == "launch":
    prev = u.GetForegroundWindow()
    subprocess.Popen([STEAM, "-applaunch", "6060", "/win", "-resolution", "1920", "1080"])
    for i in range(60):
        time.sleep(0.5)
        if game():
            break
    if not game():
        print("NO WINDOW (Steam may be showing a launch prompt)")
        sys.exit(1)
    for i in range(10):  # the window can be re-created/resized during startup
        move(); give_focus(prev); time.sleep(1)
    print("launched on monitor 2")
elif cmd == "move":
    print("moved" if move() else "no window")
elif cmd == "shot":
    shot(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 1)
elif cmd == "alive":
    sys.exit(0 if game() else 1)
elif cmd == "fg":
    print(u.GetForegroundWindow())
elif cmd == "focus":
    give_focus(int(sys.argv[2]))

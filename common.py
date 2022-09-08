from ast import While
import win32gui
import win32api
import win32con
import win32api
from win32api import GetSystemMetrics

def time_to_string(time):
    if time < 5400:
        return f"{int(time // 60.0)}m{int(time % 60.0)}s"
    else:
        return f"{int(time // 3600)}h{int((time // 60.0) % 60.0)}m{int(time % 60.0)}s"



class Window:
    def __init__(self):
        transparent_color = 0x11111

        screen_w, screen_h = GetSystemMetrics(0), GetSystemMetrics(1)

        window_handle = win32gui.CreateWindow(
            "STATIC", "", 0,
            0, 0, screen_w, screen_h,  # rect
            0, 0, win32api.GetModuleHandle(None), None
        )
        win32gui.SetWindowLong(
            window_handle, win32con.GWL_STYLE, win32con.WS_VISIBLE)
        win32gui.SetWindowLong(
            window_handle, win32con.GWL_EXSTYLE,  win32con.WS_EX_LAYERED)
        win32gui.SetLayeredWindowAttributes(
            window_handle, transparent_color, 0, win32con.LWA_COLORKEY)
        win32gui.SetWindowPos(
            window_handle, win32con.HWND_TOPMOST, 0, 0, screen_w, screen_h, 0)
        win32gui.ShowWindow(window_handle, win32con.SW_MAXIMIZE)

        self.window_handle = window_handle
        self.pen = win32gui.CreatePen(win32con.PS_SOLID, 1, 0xFF)
        self.transparent_brush = win32gui.CreateSolidBrush(transparent_color)

        self.rect((1,1,1,1))
    
    def rect(self,rect):
        dc = win32gui.GetDC(self.window_handle)
        x, y, w, h = rect
        x -= 1
        y -= 1
        w += 2
        h += 2

        whole_screen = (0, 0, GetSystemMetrics(0), GetSystemMetrics(1))

        win32gui.FillRect(dc, whole_screen, self.transparent_brush)

        win32gui.SelectObject(dc, self.pen)
        win32gui.SelectObject(dc, self.transparent_brush)

        win32gui.Rectangle(dc, x, y, x+w, y+h)

        win32gui.InvalidateRect(self.window_handle, whole_screen, True)
        # win32gui.UpdateWindow(self.window_handle)
        win32gui.ReleaseDC(self.window_handle, dc)

    def destroy(self):
        win32gui.DestroyWindow(self.window_handle)
    
    def handle(self):
        return self.window_handle

    def update(self):
        for i in range(2):
            (more,m) = win32gui.GetMessage(self.window_handle,0,10000)


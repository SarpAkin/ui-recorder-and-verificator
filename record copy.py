#!/usr/bin/python3
from email.mime import audio
from tkinter import Button
from pynput import mouse, keyboard
import json
import time
import json_names as jn
import pyautogui
import os
import sys
import shutil
import win32gui
import win32api
import win32con
import win32api
import common
from win32api import GetSystemMetrics


def print_help():
    print("""
Recording usage scenario:
    1- Enter-> .\\record.py <folder to store outputs>
    2- Prepare screen and drag your mouse to define referance rectangle to be compared by replay.py
    3- Press F9 to complete defining
    4- Press F10 to start &  stop recording
    5- Press F12 to take intermediate screenshots to compared while recording
To test enter .\\replay.py -o <output folder> [options] <file filter>
To get options enter .\\replay.py -h or .\\replay.py 
""")


def record(record_dir):

    print("drag your mouse to define capture area when done press F10 to start recording")

    os.makedirs(record_dir, exist_ok=True)

    events = []
    last_event_time = time.time()
    start_time = last_event_time

    is_recording = False

    start_stop_recording_key = keyboard.Key.f10
    screenshot_key = keyboard.Key.f12
    screenshot_area_key = keyboard.Key.f9

    last_left_click = None

    def update_window(window_hwnd):

        x, y, x_end, y_end = win32gui.GetWindowRect(window_hwnd)
        win_name = win32gui.GetWindowText(window_hwnd)

        events.insert(last_left_click, {
            jn.event_type: jn.update_window,
            jn.extends: [x, y, x_end - x, y_end - y],
            jn.window_name: win_name,
            jn.delay: 0,
        })

    def update_current_window():
        try:
            update_window(win32gui.GetForegroundWindow())
        except:
            pass

    def get_delay():
        nonlocal last_event_time
        current_time = time.time()
        delay = current_time - last_event_time
        last_event_time = current_time
        return delay

    screenshot_counter = 0
    screenshot_reigon = []
    ss_area_window_handle = 0
    ss_area_clickblock_window = 0

    transparent_color = 0x111111
    pen = win32gui.CreatePen(win32con.PS_SOLID, 1, 0xFF)
    transparent_brush = win32gui.CreateSolidBrush(transparent_color)

    def create_window():
        nonlocal ss_area_window_handle
        screen_w, screen_h = GetSystemMetrics(
            0), GetSystemMetrics(1)

        ss_area_window_handle = win32gui.CreateWindow(
            "STATIC", "", 0,
            0, 0, screen_w, screen_h,  # rect
            0, 0, win32api.GetModuleHandle(None), None
        )
        win32gui.SetWindowLong(
            ss_area_window_handle, win32con.GWL_STYLE, win32con.WS_VISIBLE)
        win32gui.SetWindowLong(
            ss_area_window_handle, win32con.GWL_EXSTYLE,  win32con.WS_EX_LAYERED)
        win32gui.SetLayeredWindowAttributes(
            ss_area_window_handle, transparent_color, 200, win32con.LWA_ALPHA)
        win32gui.SetWindowPos(ss_area_window_handle, win32con.HWND_TOPMOST, 0, 0, screen_w,
                              screen_h, 0)
        win32gui.ShowWindow(ss_area_window_handle, win32con.SW_MAXIMIZE)

        draw_rect_on_screen((1, 1, 2, 2), 0)

    def draw_rect_on_screen(rect, color):
        #hwnd = win32gui.WindowFromPoint((0, 0))
        hwnd = ss_area_window_handle
        dc = win32gui.GetDC(ss_area_window_handle)
        x, y, w, h = rect
        x -= 1
        y -= 1
        w += 2
        h += 2

        whole_screen = (0, 0, GetSystemMetrics(0), GetSystemMetrics(1))

        win32gui.FillRect(dc, whole_screen, transparent_brush)

        win32gui.SelectObject(dc, pen)
        win32gui.SelectObject(dc, transparent_brush)

        win32gui.Rectangle(dc, x, y, x+w, y+h)

        win32gui.InvalidateRect(hwnd, whole_screen, True)
        win32gui.ReleaseDC(hwnd, dc)

    def start_ss_area():
        nonlocal screenshot_reigon
        mpos = mouse.Controller().position
        screenshot_reigon = list(mpos)

    def stop_ss_area():
        nonlocal screenshot_reigon
        mpos = mouse.Controller().position
        sx = screenshot_reigon[0]
        sy = screenshot_reigon[1]
        ex, ey = mpos

        if sx == ex or sy == ey:
            print("invalid screenshot reigon")
            screenshot_reigon = []
        else:
            screenshot_reigon = create_ss_rect(sx, sy, ex, ey)
            # print(f"setting screenshot to {screenshot_reigon}")

    def create_ss_rect(sx, sy, ex, ey):
        if sx > ex:
            sx, ex = ex, sx
        if sy > ey:
            sy, ey = ey, sy

        return (sx, sy, ex - sx, ey - sy)

    def update_interactive_reigon(mpos):
        nonlocal screenshot_reigon
        if len(screenshot_reigon) != 2:
            return

        sx, sy = screenshot_reigon
        ex, ey = mpos

        draw_rect_on_screen(create_ss_rect(sx, sy, ex, ey), 0xFF)

    def screenshot():
        diff = time.time() - start_time

        nonlocal screenshot_counter
        ss_extend = None if len(screenshot_reigon) == 0 else screenshot_reigon
        # ':' results in crash on windows when used on paths for screenshotting
        ss_path = f"{record_dir}/ss_{common.time_to_string(diff)}.png"
        ss = pyautogui.screenshot(ss_path, ss_extend)
        screenshot_counter += 1
        update_mouse()

        print(f"saved screenshot to {ss_path}")

        events.append({
            jn.event_type: jn.screenshot,
            jn.screenshot: ss_path,
            jn.delay: get_delay(),
            jn.extends: ss_extend,
        })

    def on_move(x, y):
        if ss_area_window_handle == 0:
            create_window()

        if not is_recording:
            update_interactive_reigon((x, y))
            return
        events.append({jn.event_type: jn.mouse_move,
                       jn.pos: [x, y], jn.delay: get_delay()})

    def on_click(x, y, button, pressed):
        if ss_area_window_handle == 0:
            create_window()

        if not is_recording:
            if button == mouse.Button.left:
                if pressed:
                    start_ss_area()
                else:
                    stop_ss_area()

            return

        nonlocal last_left_click

        if pressed:
            if button == mouse.Button.left:
                last_left_click = len(events)

            events.append({jn.event_type: jn.mouse_press, jn.pos: [
                x, y], jn.button: button.name, jn.delay: get_delay()})

        else:
            if button == mouse.Button.left:
                update_current_window()

            events.append({jn.event_type: jn.mouse_release, jn.pos: [
                x, y], jn.button: button.name, jn.delay: get_delay()})

    def on_scroll(x, y, dx, dy):
        if not is_recording:
            return

        events.append({jn.event_type: jn.mouse_scroll, jn.pos: [
            x, y], jn.scroll: [dx, dy], jn.delay: get_delay()})

    def key_to_string(key):
        try:
            return key.vk
        except AttributeError:
            return f"{key}"

    def on_press(key):
        if not is_recording:
            return

        events.append(
            {jn.event_type: jn.key_press, jn.key: key_to_string(key), jn.delay: get_delay()})

    def update_mouse():
        x, y = mouse.Controller().position
        events.append({jn.event_type: jn.mouse_move,
                       jn.pos: [x, y], jn.delay: get_delay()})

    def start_record():
        if ss_area_window_handle == 0:
            create_window()
        
        print("started recording. Press F10 again to stop.\nYou can now press F12 at any point to take a screenshots")

        win32gui.SetLayeredWindowAttributes(ss_area_window_handle, transparent_color, 0, win32con.LWA_COLORKEY)

        # reset delay
        nonlocal start_time
        start_time = time.time()
        get_delay()
        update_mouse()

        pass

    def on_release(key):

        # if key == screenshot_area_key:
        #     start_stop_screen_shot_area()

        nonlocal is_recording
        if not is_recording:
            if key == start_stop_recording_key:
                is_recording = True
                if (len(screenshot_reigon) == 2):
                    print(
                        "unfinished screenshot reigon. You must have a valid screenshot area before starting recording")
                    exit()

                start_record()

            return

        events.append(
            {jn.event_type: jn.key_release, jn.key: key_to_string(key), jn.delay: get_delay()})

        if key == screenshot_key:
            screenshot()

        if key == start_stop_recording_key:
            # Stop listener
            screenshot()
            return False

    # ...or, in a non-blocking fashion:
    mouse_listener = mouse.Listener(
        on_move=on_move,
        on_click=on_click,
        on_scroll=on_scroll,
    )

    keyboard_listener = keyboard.Listener(
        on_press=on_press,
        on_release=on_release,
    )
    keyboard_listener.start()
    mouse_listener.start()

    keyboard_listener.join()
    print("keyboard stopped")

    mouse_listener.stop()

    with open(f"{record_dir}/session.json", "w") as file:
        json.dump({
            "ELAPSED_TIME": time.time() - start_time,
            "EVENTS": events
        }, file)


def main(args):
    if len(args) == 0:
        print_help()
        return

    record_dir = args[0]
    if os.path.exists(record_dir):
        if os.path.exists(os.path.join(record_dir, "session.json")):
            print(f"overriding {record_dir}")
        else:
            i = input(
                "overriding non record dir do you want to continue?(y/N)\n").lower()
            if not i.startswith("y"):
                return

        shutil.rmtree(record_dir)

    record(record_dir)


main(sys.argv[1:])

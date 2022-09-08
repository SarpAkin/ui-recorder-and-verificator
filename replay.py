#!/usr/bin/python3
from asyncio import events
from ctypes import byref
import pynput
from pynput.mouse import Button
from pynput.keyboard import Key, KeyCode
from pynput import mouse, keyboard
import json
import time
from parse import parse
import json_names as jn
import pyautogui
import numpy as np
from skimage.metrics import structural_similarity as compare_ssim
import cv2
import imutils
import os
import sys
import win32gui
import win32con
import re
import common
import shutil
import threading

left_handed = False


def print_help():
    print("""
To test enter .\\replay.py -o <output folder> [options] <file filter>
To get options enter .\\replay.py -h or .\\replay.py
    -o <output file> to specify replay output
    -i <regex filter> to filter recorded folders using regex, E.g. -i \"tets\\.*\"
    -f <recorded folder list> to specify a file that lists recorded tests as input (alternative of option -i)
    -t to estimate time
    -s <speed multiplier> to set replay speed, E.g. -s 2.5
    -h prints this menu and exits
""")


def sanitze_path(path):
    return os.path.normpath(path).replace("\\", "/")


failed_tests = []
speed = 1.0
window: common.Window = None


def read_json_file(path):
    with open(path) as f:
        return json.load(f)


def get_session_json(record_dir):
    with open(f"{record_dir}/session.json") as file:
        return json.load(file)


def get_record_time(record_dir):
    return get_session_json(record_dir)["ELAPSED_TIME"]


def replay(record_dir, replay_dir, replay_root):


    def get_replay_dir(dirname, n):
        path = f"{dirname}_{n}"
        if os.path.exists(path):
            return get_replay_dir(dirname, n+1)
        else:
            return path

    def get_rel_path(path):
        return os.path.relpath(path, replay_root).replace("\\", "/")

    last_time = time.time()

    def sleep_from_last(sleep_time):
        window.update()
        sleep_time *= speed

        now = time.time()
        nonlocal last_time
        amount = last_time + sleep_time - now
        if amount > 0:
            time.sleep(amount)
            last_time = now
        else:
            last_time = now + max(amount, 0.0)

    print(f"replaying {record_dir} to {replay_dir}")

    os.makedirs(replay_dir, exist_ok=True)
    logs = ""

    def print_log(s):
        nonlocal logs
        logs += f"{s}\n"

    cmouse = pynput.mouse.Controller()
    ckeyboard = pynput.keyboard.Controller()

    def button_from_string(bname):
        if not left_handed:
            if bname == "left":
                return Button.left
            elif bname == "right":
                return Button.right
        else:
            if bname == "left":
                return Button.right
            elif bname == "right":
                return Button.left

        if bname == "middle":
            return Button.middle

        print("no mouse button for {}".format(bname))

    def key_from_str(key_str):
        if type(key_str) == int:
            return KeyCode.from_vk(key_str)

        parsed_key = parse("Key.{}", key_str)
        if parsed_key is None:
            return key_str
        else:
            return Key[parsed_key[0]]

    ss_pairs = []
    ss_index = 0

    jobj = get_session_json(record_dir)
    ss_reigon = jobj["SS_REIGON"]
    events = jobj["EVENTS"]

    window.rect(ss_reigon)

    for event in events:
        sleep_from_last(event[jn.delay])
        if jn.pos in event:
            cmouse.position = event[jn.pos]

        event_type = event[jn.event_type]

        if event_type == jn.mouse_press:
            cmouse.press(button_from_string(event[jn.button]))
        elif event_type == jn.mouse_release:
            cmouse.release(button_from_string(event[jn.button]))
        elif event_type == jn.mouse_scroll:
            dx, dy = event[jn.scroll]
            cmouse.scroll(dx, dy)
        elif event_type == jn.key_press:
            ckeyboard.press(key_from_str(event[jn.key]))
        elif event_type == jn.key_release:
            ckeyboard.release(key_from_str(event[jn.key]))
        elif event_type == jn.mouse_move:
            pass
        elif event_type == jn.update_window:
            win_name = event[jn.window_name]
            win_handle = win32gui.FindWindow(None, win_name)
            if win_handle != 0:
                x, y, width, heigth = event[jn.extends]
                # win32gui.SetWindowPos(
                #     win_handle, win32con.HWND_NOTOPMOST, x, y, width, heigth, 0x0040)
                # win32gui.SetFocus(win_handle)
            else:
                print_log(
                    f"failed to find window \"{win_name}\".ignoring continuing test")
            pass
        elif event_type == jn.screenshot:
            ss_path = event[jn.screenshot]
            ss_base_path = os.path.basename(ss_path)

            ss_pairs.append(
                (ss_path, pyautogui.screenshot(f"{replay_dir}/{ss_base_path}", event[jn.extends]), ss_base_path[:ss_base_path.rfind(".png")]))

            ss_index += 1
        else:
            print("unhandled event type {}".format(event))

    # print(ss_pairs)
    print(f"finished replaying {record_dir}")

    def convert_img_to_grayscale(ss):
        return cv2.cvtColor(ss, cv2.COLOR_BGR2GRAY)

    failed_test = False

    failed_tests_in_replay = []

    for original_path, replay, base_name in ss_pairs:
        original = cv2.imread(original_path)

        replay = cv2.cvtColor(np.array(replay), cv2.COLOR_RGB2BGR)

        original_gs = convert_img_to_grayscale(original)
        replay_gs = convert_img_to_grayscale(replay)

        (score, diff) = compare_ssim(original_gs, replay_gs, full=True)
        diff = (diff * 255).astype("uint8")

        # get score from -1 : 1 to 0 : 1
        score = score * 0.5 + 0.5

        thresh = cv2.threshold(
            diff, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
        cnts = cv2.findContours(
            thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)

        for c in cnts:
            # compute the bounding box of the contour and then draw the
            # bounding box on both input images to represent where the two
            # images differ
            (x, y, w, h) = cv2.boundingRect(c)
            cv2.rectangle(original, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.rectangle(replay, (x, y), (x + w, y + h), (0, 0, 255), 2)

        original_diff_path = f"{replay_dir}/{base_name}_original_diff.png"
        replay_diff_path = f"{replay_dir}/{base_name}_replay_diff.png"

        cv2.imwrite(original_diff_path, original)
        cv2.imwrite(replay_diff_path, replay)

        if score < 0.999:
            failed_test = True
            failed_tests_in_replay.append({
                "ORIGINAL_IMAGE": get_rel_path(original_diff_path),
                "REPLAY_IMAGE": get_rel_path(replay_diff_path),
                "SCORE": score,
            })

            print_log(
                f"images {original_diff_path} {replay_diff_path} has {(1.0 - score) * 100:.2f}% difference")

        else:
            print_log(
                f"screenshot {base_name} passed with score {score * 100:.2f}%")

    if failed_test:
        print(f"failed replay: {replay_dir}")

    logfile_path = f"{replay_dir}/log"
    with open(logfile_path, "w") as logfile:
        logfile.write(logs)
        print(f"written logs into {logfile_path}")

    if failed_test:
        logs = logs.replace("\n", "\n\t")
        print(f"dumping failed tests log:\n\t{logs}")

        failed_tests.append({
            "TEST": get_rel_path(record_dir),
            "REPLAY": get_rel_path(replay_dir),
            "FAILED_TESTS": failed_tests_in_replay,
        })


def parse_directories(directories):
    def inner_parse(s: str):
        split_pos = s.rfind("/")
        if split_pos == -1:
            return None

        parsed = s[split_pos+1:]
        parsed2 = parse("{}*", parsed)
        if parsed == "*":
            parsed2 = [""]
        if parsed2 == None:
            return None

        return [s[:split_pos], parsed2[0]]

    directories = map(lambda s: s.replace("\\", "/"), directories)
    final_directories = []
    for d in directories:
        parsed = inner_parse(d)
        if parsed is None:
            final_directories.append(d)
        else:
            for d1 in os.listdir(f"{parsed[0]}"):
                if os.path.isdir(f"{parsed[0]}/{d1}") and d1.startswith(parsed[1]) if parsed[1] != "" else True:
                    final_directories.append(f"{parsed[0]}/{d1}")

    return final_directories


def parse_args_regex(arg):
    dirs = []
    regex = re.compile(arg)
    for directory, _, _ in os.walk("."):

        if regex.search(directory) != None:
            dirs.append(directory)

    return dirs


def main(args: list):
    if len(args) == 0:
        print_help()
        return

    def read_lines(file):
        with open(file) as f:
            return f.read().splitlines()

    it = iter(args + [None])
    arg = next(it)
    dirs = []
    replay_dir = None
    calc_time = False

    while arg != None:
        match arg:
            case "-o":
                replay_dir = next(it)
            case "-i":
                dirs += parse_args_regex(next(it))
            case "-f":
                file_name = next(it)
                dir_name = os.path.dirname(file_name)
                dirs += map(lambda d: os.path.join(dir_name, d.strip()),
                            read_lines(file_name))
            case "-t":
                calc_time = True
            case "-s":
                global speed
                speed = 1.0 / float(next(it))
            case "-h":
                print_help()
                return
            case other:
                dirs.append(arg)
        arg = next(it)

    if replay_dir == None:
        print("please specify a replay dir with -o")
        return

    if os.path.exists(replay_dir):
        if os.path.exists(os.path.join(replay_dir, "failed_replays.json")):
            print(f"overriding {replay_dir}")
        else:
            i = input(
                "overriding non replay  dir do you want to continue?(y/N)\n").lower()
            if not i.startswith("y"):
                return
            pass

        shutil.rmtree(replay_dir)

    dirs = parse_directories(dirs)
    dirs = list(filter(lambda d: os.path.exists(f"{d}/session.json"), dirs))

    if calc_time:
        total_time = 0.0
        for test_dir in dirs:
            total_time += get_record_time(test_dir)

        print(
            f"estimated time {common.time_to_string(total_time * speed)} with speed {1.0/speed}")

    os.mkdir(replay_dir)
    running = True



    global window
    window = common.Window()

    # mouse_listener = mouse.Listener(
    #     # on_move=on_move,
    #     # on_click=on_click,
    #     # on_scroll=on_scroll,
    # )

    # keyboard_listener = keyboard.Listener(
    #     # on_press=on_press,
    #     # on_release=on_release,
    # )
    # keyboard_listener.start()
    # mouse_listener.start()

    print(f"aaa {replay_dir}")

    for index, test_dir in enumerate(dirs):
        print(f"playing test {test_dir}  {index}/{len(dirs)}")
        replay(test_dir, sanitze_path(
            os.path.join(replay_dir, os.path.relpath(test_dir,"."))), replay_dir)

    with open(f"{replay_dir}/failed_replays.json", "w") as file:
        json.dump(failed_tests, file, indent='\t')

    with open(f"{replay_dir}/failed_replays.txt", "w") as file:
        file.writelines(map(lambda t: t["TEST"] +"\n", failed_tests))

    window.destroy()



main(sys.argv[1:])


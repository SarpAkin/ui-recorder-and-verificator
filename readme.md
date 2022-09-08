# ui recorder and verificator
records, mimics, compares and verifies guis of windows application using python.

# installing libraries
## requirements pip python 
installing the pip modules
> pip install scikit-image imutils opencv-python numpy Pillow parse pynput pyautogui pywin32

# running
run
> .\record.py
for record info

run 
> .\replay.py
for replay info

# Notes
## windows flagging as virus
add this projects forlder to virus scan exclusion by following bellow
follow https://support.microsoft.com/en-us/windows/add-an-exclusion-to-windows-security-811816c0-4dfd-af4a-47e4-c301afe13b26#:~:text=Go%20to%20Start%20%3E%20Settings%20%3E%20Update,%2C%20file%20types%2C%20or%20process.


## left handed mouse 
if you notice mouse clicks not registering during replay 
goto the line containing "left_handed=False" in replay.py
and set it to "left_handed=True" 

 

from pynput import keyboard
import pyperclip

import pyautogui
from pyautogui import press, typewrite, hotkey, write

modifier_pressed = False
wait_for_next_copy = False
wait_for_next_paste = False

saved = [ '' for x in range (10) ]

def copy (received):
    print (F"C: {pyperclip.paste ()}")
    nreceived = int (received)
    saved[nreceived] = pyperclip.paste ()

def paste (received):
    nreceived = int (received)
    new = saved[nreceived]
    pyperclip.copy ('')

    if (len (new) != 0):
        print (F"V: {new}")
        pyperclip.copy (new)

def on_press(key):
    global modifier_pressed
    global wait_for_next_copy
    global wait_for_next_paste

    try:
        if (key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r) and (key == keyboard.Key.alt_l or key == keyboard.Key.alt_r):
            modifier_pressed = True

        elif (key.char.lower() == 'c' and modifier_pressed) or wait_for_next_copy:
            wait_for_next_copy = True

            if (wait_for_next_copy and key.char.lower () in '0123456789'):
                copy (key.char.lower ())
                wait_for_next_copy = False

        elif (key.char.lower() == 'v' and modifier_pressed) or wait_for_next_paste:
            wait_for_next_paste = True

            if (wait_for_next_paste and key.char.lower () in '0123456789'):
                paste (key.char.lower ())
                wait_for_next_paste = False

        elif (key.char.lower () == '`'):
            for x in range (len (saved)):
                print (F"{x}: {saved[x]}")
            print ('\n')

    except AttributeError:
        pass

def on_release(key):
    global modifier_pressed

    if key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
        modifier_pressed = False


def main ():
    # Start the listener
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join ()

if (__name__ == "__main__"):
    main ()

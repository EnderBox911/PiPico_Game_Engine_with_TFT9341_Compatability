from machine import Pin
from Engine.engine_core import InputState

PIN_UP = 21
PIN_DOWN = 20
PIN_LEFT = 19
PIN_RIGHT = 18

btn_up = Pin(PIN_UP, Pin.IN, Pin.PULL_UP)
btn_down = Pin(PIN_DOWN, Pin.IN, Pin.PULL_UP)
btn_left = Pin(PIN_LEFT, Pin.IN, Pin.PULL_UP)
btn_right = Pin(PIN_RIGHT, Pin.IN, Pin.PULL_UP)


def read_input_state():
    """
    Read physical buttons and return an InputState object.
    Buttons wired to GND with PULL_UP, so pressed = 0
    :return: InputState
    """
    s = InputState()
    s.up = (btn_up.value() == 0)
    s.down = (btn_down.value() == 0)
    s.left = (btn_left.value() == 0)
    s.right = (btn_right.value() == 0)

    # no a/b yet, is kept as false
    return s
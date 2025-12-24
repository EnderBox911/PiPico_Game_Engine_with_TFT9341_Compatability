# Pico Game Engine

A lightweight game engine written in **MicroPython** for the **Raspberry Pi Pico**, designed to run games directly on microcontroller hardware with no operating system or framebuffer.

The engine includes a full input system, graphics abstraction, sprite rendering, and game state management. A complete **Blackjack** game is included as a demo.

---

## Features

- Custom game loop with fixed target FPS
- Button input handling with edge detection
- Simple but powerful graphics API
- RGB565 sprite rendering
- Text rendering with scaling and caching
- Partial redraw system for performance
- Game reset support
- Designed for very low RAM environments
- Runs entirely on bare-metal microcontroller hardware

---

## Hardware Requirements

- Raspberry Pi Pico or Pico W
- ILI9341 TFT display (SPI)
- Push buttons (UP, DOWN, LEFT, RIGHT)
- Optional breadboard / wiring

---

## Project Structure

```
├── Engine/
│ ├── engine_core.py # Main game loop and input handling
│ ├── game_base.py # Base class for games
│ └── gfx_pico.py # Graphics abstraction layer
│
├── Driver/
│ └── tft_ili9341.py # Low-level ILI9341 display driver
│
├── Games/
│ └── Blackjack/
│     └── blackjack.py # Blackjack game implementation
│     └── bin_files/ # RGB565 sprite assets (.bin)
│
└── main.py # Entry point
```
---


## How the Engine Works

### Game Loop

The engine runs a fixed-timestep loop:
1. Read input
2. Dispatch input events
3. Update the active game
4. Redraw only if needed
5. Frame-rate limiting

Each game inherits from `GameBase` and implements:

```python
update(self, dt, input_state)
draw(self, gfx)
````

---

### Input System

Buttons are polled each frame and converted into:

* Held states (`up`, `down`, etc.)
* Edge events (`up_pressed`, `down_pressed`, etc.)

Games can optionally implement:

```python
on_up_pressed()
on_left_pressed()
```

---

### Graphics System

The `PicoGFX` layer abstracts the display and provides:

* `fill_rect()`
* `draw_text()`
* `draw_sprite()`
* `safe_fill_rect()`

All drawing is done directly over SPI using RGB565 data.

---

### Sprites

Sprites are stored as raw `.bin` files in RGB565 format and loaded on demand.
Sprites are cached to avoid repeated file reads.

---

## Blackjack Demo

The included Blackjack game demonstrates:

* Game states
* Sprite-based card rendering
* Partial redraws
* Memory cleanup between rounds
* Real-time user input

Controls:

* **LEFT** → Hit
* **RIGHT** → Stand
* **UP (double-tap)** → Reset round

---

## Running the Project

1. Flash MicroPython onto the Pico
2. Copy all files to the Pico filesystem
3. Place card `.bin` files into `/bin_files`
4. Run `main.py`

---

## Why This Project

This project was built to explore:

* How game engines work at a low level
* Graphics programming without a framebuffer
* Efficient rendering on constrained hardware
* Embedded systems + game development


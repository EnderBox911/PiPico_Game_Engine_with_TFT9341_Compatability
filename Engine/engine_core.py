import time


class InputState:
    def __init__(self):
        self.up = False
        self.down = False
        self.left = False
        self.right = False
        self.a = False
        self.b = False

        self.up_pressed = False
        self.down_pressed = False
        self.left_pressed = False
        self.right_pressed = False
        self.a_pressed = False
        self.b_pressed = False


class Engine:
    def __init__(self, gfx, target_fps=30, input_provider=None):
        self.gfx = gfx
        self.target_fps = target_fps
        self.frame_time = 1.0 / target_fps

        self.input_provider = input_provider
        self._current_input = InputState()
        self._prev_input = InputState()
        self._running = True

        self._last_up_press_time = None
        self._double_tap_threshold_ms = 400  # 0.4s window

    # ----- input handling -----
    def _update_input(self):
        if self.input_provider is None:
            raw = InputState()
        else:
            raw = self.input_provider()

        prev = self._current_input
        cur = InputState()

        cur.up = raw.up
        cur.down = raw.down
        cur.left = raw.left
        cur.right = raw.right
        cur.a = raw.a
        cur.b = raw.b

        cur.up_pressed = cur.up and not prev.up
        cur.down_pressed = cur.down and not prev.down
        cur.left_pressed = cur.left and not prev.left
        cur.right_pressed = cur.right and not prev.right
        cur.a_pressed = cur.a and not prev.a
        cur.b_pressed = cur.b and not prev.b

        self._prev_input = prev
        self._current_input = cur

    def _dispatch_input_events(self, game):
        """
        Call optional callbacks on the game when buttons are just pressed.
        Game can define:
            on_up_pressed(self)
            on_down_pressed(self)
            on_left_pressed(self)
            on_right_pressed(self)
            on_a_pressed(self)
            on_b_pressed(self)
        """
        s = self._current_input

        if s.up_pressed and hasattr(game, "on_up_pressed"):
            game.on_up_pressed()
        if s.down_pressed and hasattr(game, "on_down_pressed"):
            game.on_down_pressed()
        if s.left_pressed and hasattr(game, "on_left_pressed"):
            game.on_left_pressed()
        if s.right_pressed and hasattr(game, "on_right_pressed"):
            game.on_right_pressed()
        if s.a_pressed and hasattr(game, "on_a_pressed"):
            game.on_a_pressed()
        if s.b_pressed and hasattr(game, "on_b_pressed"):
            game.on_b_pressed()

    @property
    def input_state(self):
        return self._current_input

    # ----- main loop -----
    def run(self, game):
        self._running = True
        last_time = time.ticks_ms()
        first_frame = True

        while self._running:
            now = time.ticks_ms()
            dt_ms = time.ticks_diff(now, last_time)
            last_time = now
            dt = dt_ms / 1000.0

            # 1) input
            self._update_input()
            self._dispatch_input_events(game)

            # --- detect double-tap on UP (reset) ---
            if self._current_input.up_pressed:
                if self._last_up_press_time is not None:
                    diff = time.ticks_diff(now, self._last_up_press_time)
                    if diff <= self._double_tap_threshold_ms:
                        self._last_up_press_time = None
                        if hasattr(game, "reset"):
                            game.reset()
                        continue
                    else:
                        self._last_up_press_time = now
                else:
                    self._last_up_press_time = now

            # 2) game logic
            game.update(dt, self._current_input)

            # 3) draw only if needed
            should_draw = True
            if hasattr(game, "should_redraw"):
                should_draw = game.should_redraw() or first_frame

            if should_draw:
                game.draw(self.gfx)
                self.gfx.present()

            first_frame = False

            # 4) frame limiting
            elapsed_ms = time.ticks_diff(time.ticks_ms(), now)
            spare = int(self.frame_time * 1000) - elapsed_ms
            if spare > 0:
                time.sleep_ms(spare)

    def stop(self):
        self._running = False

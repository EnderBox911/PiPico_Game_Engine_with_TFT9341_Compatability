# Engine/game_base.py


class GameBase:
    """
    Base class for all games.

    Games can override:
      - update(self, dt, input_state)
      - draw(self, gfx)
      - reset(self)
      - on_*_pressed callbacks for input events
    """

    def __init__(self, engine):
        self.engine = engine
        self.needs_redraw = True

    def update(self, dt, input_state):
        pass

    def draw(self, gfx):
        pass

    def should_redraw(self):
        return self.needs_redraw

    def request_redraw(self):
        self.needs_redraw = True

    def reset(self):
        """
        Default hard reset: re-run __init__ with the same engine.

        Games can override this to provide a custom reset that only
        resets some state (for example, start a new round).
        """
        self.__init__(self.engine)

    # Optional input hooks (games override these if they want them)
    def on_up_pressed(self):
        pass

    def on_down_pressed(self):
        pass

    def on_left_pressed(self):
        pass

    def on_right_pressed(self):
        pass

    def on_a_pressed(self):
        pass

    def on_b_pressed(self):
        pass

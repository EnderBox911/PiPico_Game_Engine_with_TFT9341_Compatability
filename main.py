# main.py
from Engine.engine_core import Engine
from Engine.gfx_pico import PicoGFX
from Engine.input_pico import read_input_state
from Games.Blackjack.blackjack import BlackjackGame


def main():
    gfx = PicoGFX()
    engine = Engine(gfx, target_fps=30, input_provider=read_input_state)
    game = BlackjackGame(engine)
    engine.run(game)


main()

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.game import Game


def main():
    game = Game()
    game.run()


if __name__ == "__main__":
    main()

from engine import GameEngine
from ui import SnakeApp

def main() -> None:
    SnakeApp(GameEngine()).run()

if __name__ == "__main__":
    main()

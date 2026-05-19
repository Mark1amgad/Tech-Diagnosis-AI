import sys
from ui.app import launch_app

def main():
    try:
        launch_app()
    except KeyboardInterrupt:
        print("\nExiting Advanced KBS...")
        sys.exit(0)

if __name__ == "__main__":
    main()

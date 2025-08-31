from consts import PATH
from gui import MusicRankingApp
import os

if __name__ == "__main__":
    # *** Make sure to change all parameters in consts.py ***

    if not os.path.exists(PATH):
        os.makedirs(PATH, exist_ok=True)

    app = MusicRankingApp()
    app.mainloop()

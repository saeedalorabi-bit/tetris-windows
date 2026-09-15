import os

# Update to your Proxmox server LAN IP
SERVER_URL = "http://192.168.100.2:8000"
TOKEN_FILE = os.path.join(os.path.expanduser("~"), ".tetris_token.json")

WIDTH, HEIGHT = 800, 700
PLAY_WIDTH, PLAY_HEIGHT = 300, 600
BLOCK_SIZE = 30
TOP_LEFT_X = (WIDTH - PLAY_WIDTH) // 2
TOP_LEFT_Y = HEIGHT - PLAY_HEIGHT - 50

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
GOLD = (255, 215, 0)
SILVER = (192, 192, 192)
BRONZE = (205, 127, 50)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
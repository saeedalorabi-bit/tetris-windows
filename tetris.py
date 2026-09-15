import pygame
import random
import io
import wave
import struct
import math
import api, auth, sounds
from settings import *

pygame.init()
pygame.font.init()

font = pygame.font.SysFont("comicsans", 30)
small_font = pygame.font.SysFont("comicsans", 20)

win = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Tetris HomeLab Edition")

BOARD_WIDTH = 10
BOARD_HEIGHT = 20
PANEL_WIDTH = 250

SCREEN_WIDTH = (BOARD_WIDTH * BLOCK_SIZE) + PANEL_WIDTH
SCREEN_HEIGHT = BOARD_HEIGHT * BLOCK_SIZE

BOARD_BG = (20, 20, 20)
GRID_COLOR = (40, 40, 40)
TEXT_COLOR = (240, 240, 240)
GREEN_TEXT = (50, 255, 50)
HIGHLIGHT_COLOR = (255, 255, 0)

COLORS = [
    (0, 255, 255),   # I - Cyan
    (255, 255, 0),   # O - Yellow
    (128, 0, 128),   # T - Purple
    (0, 255, 0),     # S - Green
    (255, 0, 0),     # Z - Red
    (0, 0, 255),     # J - Blue
    (255, 165, 0)    # L - Orange
]

SHAPES = [
    [[0, 0, 0, 0], [1, 1, 1, 1], [0, 0, 0, 0], [0, 0, 0, 0]],  # I
    [[1, 1], [1, 1]],                                          # O
    [[0, 1, 0], [1, 1, 1], [0, 0, 0]],                         # T
    [[0, 1, 1], [1, 1, 0], [0, 0, 0]],                         # S
    [[1, 1, 0], [0, 1, 1], [0, 0, 0]],                         # Z
    [[1, 0, 0], [1, 1, 1], [0, 0, 0]],                         # J
    [[0, 0, 1], [1, 1, 1], [0, 0, 0]]                          # L
]

font_main = pygame.font.SysFont('arial', 24)
font_title = pygame.font.SysFont('arial', 36, bold=True)
font_large = pygame.font.SysFont('arial', 48, bold=True)


def generate_sound(frequency, duration, volume=0.1, wave_type='square'):
    """Generates an 8-bit style sound effect in memory safely."""
    if not pygame.mixer.get_init():
        return None
    try:
        sample_rate = 44100
        num_samples = int(sample_rate * duration)
        wav_file = io.BytesIO()
        with wave.open(wav_file, 'w') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)

            for i in range(num_samples):
                t = float(i) / sample_rate
                val = 1.0 if math.sin(2 * math.pi * frequency * t) > 0 else -1.0
                fade = 1.0 - (i / num_samples)
                value = int(volume * 32767.0 * val * fade)
                wav.writeframesraw(struct.pack('<h', value))

        wav_file.seek(0)
        return pygame.mixer.Sound(wav_file)
    except Exception:
        return None


def generate_arpeggio(freqs, step_duration, volume=0.1):
    """Generates an 8-bit style arpeggio (succession of notes) for level clears."""
    if not pygame.mixer.get_init():
        return None
    try:
        sample_rate = 44100
        wav_file = io.BytesIO()
        with wave.open(wav_file, 'w') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)

            for freq in freqs:
                num_samples = int(sample_rate * step_duration)
                for i in range(num_samples):
                    t = float(i) / sample_rate
                    val = 1.0 if math.sin(2 * math.pi * freq * t) > 0 else -1.0
                    fade = 1.0 - (i / float(num_samples))
                    value = int(volume * 32767.0 * val * fade)
                    wav.writeframesraw(struct.pack('<h', value))
        wav_file.seek(0)
        return pygame.mixer.Sound(wav_file)
    except Exception:
        return None


SND_MOVE = generate_sound(150, 0.05, volume=0.08)
SND_CLEAR_1 = generate_arpeggio([440, 554, 659], 0.1, volume=0.1)
SND_CLEAR_4 = generate_arpeggio([440, 554, 659, 880, 1108], 0.08, volume=0.1)


class Tetromino:
    def __init__(self):
        self.shape_idx = random.randint(0, len(SHAPES) - 1)
        self.shape = SHAPES[self.shape_idx]
        self.color = COLORS[self.shape_idx]
        self.x = BOARD_WIDTH // 2 - len(self.shape[0]) // 2
        self.y = 0

    def rotate(self):
        self.shape = [list(row) for row in zip(*self.shape[::-1])]


class Game:
    def __init__(self):
        self.base_speed_ms = 1000
        self.settings_index = 0
        self.settings_options = ["Base Speed", "Reset Default", "Back"]

        self.reset_game()
        self.state = "START"

    def reset_game(self):
        self.board = [[0 for _ in range(BOARD_WIDTH)] for _ in range(BOARD_HEIGHT)]
        self.current_piece = Tetromino()
        self.next_piece = Tetromino()
        self.score = 0
        self.level = 1
        self.lines = 0

        self.fall_time = 0
        self.paused = False
        self.score_notifications = []

    def get_current_speed(self):
        """Calculates current falling speed: base speed increases 10% per 1000 pts."""
        multiplier = 1.1 ** (self.score // 1000)
        actual_speed = self.base_speed_ms / multiplier
        return max(50, int(actual_speed))

    def valid_move(self, piece, x_offset, y_offset):
        for y, row in enumerate(piece.shape):
            for x, cell in enumerate(row):
                if cell:
                    new_x = piece.x + x + x_offset
                    new_y = piece.y + y + y_offset
                    if new_x < 0 or new_x >= BOARD_WIDTH or new_y >= BOARD_HEIGHT:
                        return False
                    if new_y >= 0 and self.board[new_y][new_x] != 0:
                        return False
        return True

    def lock_piece(self):
        for y, row in enumerate(self.current_piece.shape):
            for x, cell in enumerate(row):
                if cell:
                    if self.current_piece.y + y < 0:
                        self.state = "GAME_OVER"
                        return
                    self.board[self.current_piece.y + y][self.current_piece.x + x] = self.current_piece.color

        self.clear_lines()
        self.current_piece = self.next_piece
        self.next_piece = Tetromino()

        if not self.valid_move(self.current_piece, 0, 0):
            self.state = "GAME_OVER"

    def clear_lines(self):
        lines_to_clear = [y for y in range(BOARD_HEIGHT) if all(self.board[y])]
        num_lines = len(lines_to_clear)

        if num_lines > 0:
            for y in lines_to_clear:
                del self.board[y]
                self.board.insert(0, [0 for _ in range(BOARD_WIDTH)])

            points_earned = 0
            if num_lines == 1:
                points_earned = 100 * self.level
            elif num_lines == 2:
                points_earned = 300 * self.level
            elif num_lines == 3:
                points_earned = 500 * self.level
            elif num_lines == 4:
                points_earned = 800 * self.level

            self.score += points_earned
            self.lines += num_lines
            self.level = self.lines // 10 + 1

            if num_lines >= 4 and SND_CLEAR_4:
                SND_CLEAR_4.play()
            elif SND_CLEAR_1:
                SND_CLEAR_1.play()

            self.score_notifications.append({
                "text": f"+{points_earned}",
                "y_offset": 0,
                "time": 1000
            })

    def move(self, dx, dy):
        if self.valid_move(self.current_piece, dx, dy):
            self.current_piece.x += dx
            self.current_piece.y += dy

            if dx != 0 and SND_MOVE:
                SND_MOVE.play()
            return True
        elif dy > 0:
            self.lock_piece()
        return False

    def rotate(self):
        original_shape = self.current_piece.shape
        self.current_piece.rotate()
        if not self.valid_move(self.current_piece, 0, 0):
            self.current_piece.shape = original_shape
        elif SND_MOVE:
            SND_MOVE.play()

    def hard_drop(self):
        drop_distance = 0
        while self.valid_move(self.current_piece, 0, 1):
            self.current_piece.y += 1
            drop_distance += 1
        
        # Award 2 points per block dropped instantly
        if drop_distance > 0:
            self.score += drop_distance * 2

        self.lock_piece()

    def update(self, delta_time):
        for notif in self.score_notifications[:]:
            notif['time'] -= delta_time
            notif['y_offset'] -= (0.04 * delta_time)
            if notif['time'] <= 0:
                self.score_notifications.remove(notif)

        if self.state != "PLAYING" or self.paused:
            return

        keys = pygame.key.get_pressed()
        is_soft_dropping = keys[pygame.K_DOWN]

        current_speed = self.get_current_speed()
        if is_soft_dropping:
            current_speed = 40

        self.fall_time += delta_time
        if self.fall_time >= current_speed:
            if self.move(0, 1) and is_soft_dropping:
                self.score += 1
            self.fall_time = 0

    def draw_board(self, surface):
        surface.fill(BOARD_BG)
        for y in range(BOARD_HEIGHT):
            for x in range(BOARD_WIDTH):
                if self.board[y][x] != 0:
                    pygame.draw.rect(surface, self.board[y][x],
                                      (x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE - 1, BLOCK_SIZE - 1))

        for y in range(BOARD_HEIGHT):
            pygame.draw.line(surface, GRID_COLOR, (0, y * BLOCK_SIZE), (BOARD_WIDTH * BLOCK_SIZE, y * BLOCK_SIZE))
        for x in range(BOARD_WIDTH):
            pygame.draw.line(surface, GRID_COLOR, (x * BLOCK_SIZE, 0), (x * BLOCK_SIZE, SCREEN_HEIGHT))

        pygame.draw.line(surface, WHITE, (BOARD_WIDTH * BLOCK_SIZE, 0), (BOARD_WIDTH * BLOCK_SIZE, SCREEN_HEIGHT), 2)

    def draw_piece(self, surface, piece, offset_x=0, offset_y=0):
        for y, row in enumerate(piece.shape):
            for x, cell in enumerate(row):
                if cell:
                    px = (piece.x + x) * BLOCK_SIZE + offset_x
                    py = (piece.y + y) * BLOCK_SIZE + offset_y
                    if py >= 0:
                        pygame.draw.rect(surface, piece.color, (px, py, BLOCK_SIZE - 1, BLOCK_SIZE - 1))

    def draw_ui(self, surface):
        next_label = font_main.render('Next Piece:', True, TEXT_COLOR)
        surface.blit(next_label, (BOARD_WIDTH * BLOCK_SIZE + 20, 20))

        temp_x, temp_y = self.next_piece.x, self.next_piece.y
        self.next_piece.x, self.next_piece.y = 0, 0
        self.draw_piece(surface, self.next_piece, offset_x=BOARD_WIDTH * BLOCK_SIZE + 50, offset_y=60)
        self.next_piece.x, self.next_piece.y = temp_x, temp_y

        stats = [
            (f"Score: {self.score}", 200),
            (f"Level: {self.level}", 250),
            (f"Lines: {self.lines}", 300)
        ]

        for text, y_pos in stats:
            label = font_main.render(text, True, TEXT_COLOR)
            surface.blit(label, (BOARD_WIDTH * BLOCK_SIZE + 20, y_pos))

        for notif in self.score_notifications:
            alpha = max(0, min(255, int((notif['time'] / 1000) * 255)))
            text_surf = font_main.render(notif['text'], True, GREEN_TEXT)
            text_surf.set_alpha(alpha)
            surface.blit(text_surf, (BOARD_WIDTH * BLOCK_SIZE + 160, 200 + notif['y_offset']))

        controls = [
            "ESC: Settings",
            "Arrows: Move",
            "Up: Rotate",
            "Hold Down: Soft Drop",
            "Space: Hard Drop",
            "P: Pause / R: Restart",
            "M: Menu"
        ]
        for i, text in enumerate(controls):
            label = pygame.font.SysFont('arial', 16).render(text, True, GRAY)
            surface.blit(label, (BOARD_WIDTH * BLOCK_SIZE + 10, 420 + (i * 25)))

    def draw_overlays(self, surface):
        if self.state == "START":
            self.draw_center_text(surface, "TETRIS", "Press Space to start", COLORS[0])
        elif self.state == "GAME_OVER":
            self.draw_center_text(surface, "GAME OVER", "R: Restart   M: Menu", COLORS[4])
        elif self.paused:
            self.draw_center_text(surface, "PAUSED", "Press P to resume", COLORS[1])
        elif self.state == "SETTINGS":
            self.draw_settings(surface)

    def draw_center_text(self, surface, title, subtitle, title_color):
        title_surf = font_large.render(title, True, title_color)
        subtitle_surf = font_main.render(subtitle, True, WHITE)

        bg_rect = pygame.Surface((BOARD_WIDTH * BLOCK_SIZE, 120))
        bg_rect.set_alpha(210)
        bg_rect.fill(BOARD_BG)
        surface.blit(bg_rect, (0, SCREEN_HEIGHT // 2 - 60))

        surface.blit(title_surf, ((BOARD_WIDTH * BLOCK_SIZE - title_surf.get_width()) // 2, SCREEN_HEIGHT // 2 - 50))
        surface.blit(subtitle_surf, ((BOARD_WIDTH * BLOCK_SIZE - subtitle_surf.get_width()) // 2, SCREEN_HEIGHT // 2 + 10))

    def draw_settings(self, surface):
        bg_rect = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        bg_rect.set_alpha(230)
        bg_rect.fill(BOARD_BG)
        surface.blit(bg_rect, (0, 0))

        title = font_large.render("SETTINGS", True, WHITE)
        surface.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 80))

        for i, option in enumerate(self.settings_options):
            color = HIGHLIGHT_COLOR if i == self.settings_index else GRAY

            text = option
            if i == 0:
                text = f"< {option}: {self.base_speed_ms} ms >"

            label = font_main.render(text, True, color)
            surface.blit(label, (SCREEN_WIDTH // 2 - label.get_width() // 2, 200 + i * 50))

        tip = pygame.font.SysFont('arial', 16).render("Up/Down to select | Left/Right to change | Enter to confirm", True, GRAY)
        surface.blit(tip, (SCREEN_WIDTH // 2 - tip.get_width() // 2, 400))


class TextInput:
    def __init__(self, x, y, w, h, is_password=False):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = GRAY
        self.text = ""
        self.active = False
        self.is_password = is_password

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
            self.color = WHITE if self.active else GRAY
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif len(self.text) < 20:
                self.text += event.unicode

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect, 2)
        display_str = "*" * len(self.text) if self.is_password else self.text
        txt_surface = font.render(display_str, True, WHITE)
        surface.blit(txt_surface, (self.rect.x + 5, self.rect.y + 5))


class Button:
    def __init__(self, x, y, w, h, text):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text

    def draw(self, surface):
        pygame.draw.rect(surface, WHITE, self.rect, 2)
        txt = font.render(self.text, True, WHITE)
        surface.blit(txt, (self.rect.x + (self.rect.w - txt.get_width()) // 2, self.rect.y + 10))

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)


class GameApp:
    def __init__(self):
        self.state = "LOGIN"
        self.token = None
        self.username = ""
        self.high_score = 0
        self.stay_signed_in = True
        self.msg = ""
        self.board_data = []
        
        self.inp_user = TextInput(300, 180, 200, 40)
        self.inp_pass = TextInput(300, 240, 200, 40, True)
        self.inp_pass2 = TextInput(300, 300, 200, 40, True)
        
        self.btn_login = Button(300, 350, 200, 40, "Login")
        self.btn_switch_signup = Button(300, 410, 200, 40, "Go to Sign Up")
        self.btn_signup = Button(300, 370, 200, 40, "Sign Up")
        self.btn_switch_login = Button(300, 430, 200, 40, "Go to Login")
        self.btn_play = Button(300, 200, 200, 40, "Play Game")
        self.btn_leaderboard = Button(300, 260, 200, 40, "Leaderboard")
        self.btn_logout = Button(300, 320, 200, 40, "Logout")
        self.btn_back = Button(300, 600, 200, 40, "Back")
        
        self.checkbox = pygame.Rect(300, 305, 20, 20)

        saved = auth.load_token()
        if saved:
            self.token = saved['token']
            self.username = saved['username']
            self.high_score = saved['high_score']
            self.state = "MENU"

    def run(self):
        clock = pygame.time.Clock()
        run = True
        while run:
            win.fill(BLACK)
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    run = False
            
            if self.state == "LOGIN":
                self.draw_login(events)
            elif self.state == "SIGNUP":
                self.draw_signup(events)
            elif self.state == "MENU":
                self.draw_menu(events)
            elif self.state == "LEADERBOARD":
                self.draw_leaderboard(events)
            elif self.state == "GAME":
                self.run_game()
            
            pygame.display.update()
            clock.tick(60)

    def draw_login(self, events):
        # Keep login fields in their normal positions
        self.inp_user.rect.y = 180
        self.inp_pass.rect.y = 240

        title = font.render("Login to HomeLab", True, WHITE)
        win.blit(title, (WIDTH//2 - title.get_width()//2, 100))
        
        win.blit(small_font.render("Username:", True, WHITE), (300, 155))
        win.blit(small_font.render("Password:", True, WHITE), (300, 215))
        
        self.inp_user.draw(win)
        self.inp_pass.draw(win)
        
        pygame.draw.rect(win, WHITE, self.checkbox, 2)
        if self.stay_signed_in:
            pygame.draw.rect(win, WHITE, self.checkbox.inflate(-6, -6))
        win.blit(small_font.render("Stay signed in", True, WHITE), (330, 305))
        
        self.btn_login.draw(win)
        self.btn_switch_signup.draw(win)
        
        if self.msg:
            err = small_font.render(self.msg, True, RED)
            win.blit(err, (WIDTH//2 - err.get_width()//2, 480))

        for event in events:
            self.inp_user.handle_event(event)
            self.inp_pass.handle_event(event)

            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.checkbox.collidepoint(event.pos):
                    self.stay_signed_in = not self.stay_signed_in

                if self.btn_switch_signup.is_clicked(event.pos):
                    self.state = "SIGNUP"
                    self.msg = ""

                if self.btn_login.is_clicked(event.pos):
                    success, res = api.login(self.inp_user.text, self.inp_pass.text)

                    if success:
                        self.token = res['token']
                        self.username = self.inp_user.text
                        self.high_score = res['high_score']

                        if self.stay_signed_in:
                            auth.save_token(
                                self.username,
                                self.token,
                                self.high_score
                            )

                        self.state = "MENU"
                        self.msg = ""
                    else:
                        self.msg = res

    def draw_signup(self, events):
        # Move signup fields higher so they line up with the labels
        self.inp_user.rect.y = 120
        self.inp_pass.rect.y = 180
        self.inp_pass2.rect.y = 240

        title = font.render("Sign Up", True, WHITE)
        win.blit(title, (WIDTH//2 - title.get_width()//2, 50))
        
        win.blit(small_font.render("Username:", True, WHITE), (300, 95))
        win.blit(small_font.render("Password:", True, WHITE), (300, 155))
        win.blit(small_font.render("Confirm Password:", True, WHITE), (300, 215))
        
        self.inp_user.draw(win)
        self.inp_pass.draw(win)
        self.inp_pass2.draw(win)
        
        self.btn_signup.draw(win)
        self.btn_switch_login.draw(win)
        
        if self.msg:
            err = small_font.render(self.msg, True, RED)
            win.blit(err, (WIDTH//2 - err.get_width()//2, 490))

        for event in events:
            self.inp_user.handle_event(event)
            self.inp_pass.handle_event(event)
            self.inp_pass2.handle_event(event)

            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.btn_switch_login.is_clicked(event.pos):
                    self.state = "LOGIN"
                    self.msg = ""

                if self.btn_signup.is_clicked(event.pos):
                    if self.inp_pass.text != self.inp_pass2.text:
                        self.msg = "Password and Confirm Password must match."
                        continue

                    prof_err = auth.local_profanity_check(self.inp_user.text)

                    if prof_err:
                        self.msg = prof_err
                        continue
                        
                    success, res = api.register(
                        self.inp_user.text,
                        self.inp_pass.text
                    )

                    if success:
                        self.msg = "Registration successful! Please login."
                        self.state = "LOGIN"
                    else:
                        self.msg = res

    def draw_menu(self, events):
        title = font.render(f"Welcome, {self.username}!", True, WHITE)
        win.blit(title, (WIDTH//2 - title.get_width()//2, 100))
        pb = small_font.render(f"Personal Best: {self.high_score}", True, GOLD)
        win.blit(pb, (WIDTH//2 - pb.get_width()//2, 150))
        
        self.btn_play.draw(win)
        self.btn_leaderboard.draw(win)
        self.btn_logout.draw(win)
        
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.btn_play.is_clicked(event.pos):
                    self.state = "GAME"

                if self.btn_leaderboard.is_clicked(event.pos):
                    self.board_data = api.get_leaderboard()
                    self.state = "LEADERBOARD"

                if self.btn_logout.is_clicked(event.pos):
                    auth.clear_token()
                    self.token = None
                    self.state = "LOGIN"

    def draw_leaderboard(self, events):
        title = font.render("LEADERBOARD", True, WHITE)
        win.blit(title, (WIDTH//2 - title.get_width()//2, 50))
        
        y_offset = 120

        if not self.board_data:
            no_data = small_font.render("No scores yet.", True, WHITE)
            win.blit(no_data, (WIDTH//2 - no_data.get_width()//2, y_offset))
        else:
            for i, entry in enumerate(self.board_data):
                color = WHITE
                prefix = f"{i+1}."

                if i == 0: 
                    color, prefix = GOLD, "🥇"
                elif i == 1: 
                    color, prefix = SILVER, "🥈"
                elif i == 2: 
                    color, prefix = BRONZE, "🥉"
                
                txt = font.render(
                    f"{prefix} {entry['username']}    {entry['score']}",
                    True,
                    color
                )

                win.blit(txt, (250, y_offset))
                y_offset += 40
            
        self.btn_back.draw(win)

        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.btn_back.is_clicked(event.pos):
                    self.state = "MENU"

    def run_game(self):
        game = Game()
        clock = pygame.time.Clock()
        pygame.key.set_repeat(200, 50)
        last_milestone = 0
        submitted = False
        running = True

        while running:
            delta_time = clock.tick(60)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    self.state = "MENU"

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if game.state in ["PLAYING", "START", "GAME_OVER"]:
                            game.previous_state = game.state
                            game.state = "SETTINGS"
                        elif game.state == "SETTINGS":
                            game.state = getattr(game, 'previous_state', "START")

                    elif game.state == "SETTINGS":
                        if event.key == pygame.K_UP:
                            game.settings_index = (game.settings_index - 1) % len(game.settings_options)

                        elif event.key == pygame.K_DOWN:
                            game.settings_index = (game.settings_index + 1) % len(game.settings_options)

                        elif event.key == pygame.K_LEFT and game.settings_index == 0:
                            game.base_speed_ms = max(100, game.base_speed_ms - 100)

                        elif event.key == pygame.K_RIGHT and game.settings_index == 0:
                            game.base_speed_ms = min(2000, game.base_speed_ms + 100)

                        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                            if game.settings_index == 1:
                                game.base_speed_ms = 1000

                            elif game.settings_index == 2:
                                game.state = getattr(
                                    game,
                                    'previous_state',
                                    "START"
                                )

                        continue

                    if game.state == "START":
                        if event.key == pygame.K_SPACE:
                            game.state = "PLAYING"

                    elif game.state == "GAME_OVER":
                        if event.key == pygame.K_r:
                            game.reset_game()
                            game.state = "PLAYING"
                            last_milestone = 0
                            submitted = False

                        elif event.key == pygame.K_m:
                            running = False
                            self.state = "MENU"

                    elif game.state == "PLAYING":
                        if event.key == pygame.K_p:
                            game.paused = not game.paused

                        if not game.paused:
                            if event.key == pygame.K_LEFT:
                                game.move(-1, 0)

                            elif event.key == pygame.K_RIGHT:
                                game.move(1, 0)

                            elif event.key == pygame.K_UP:
                                game.rotate()

                            elif event.key == pygame.K_SPACE:
                                pygame.key.set_repeat(0, 0)
                                game.hard_drop()
                                pygame.key.set_repeat(200, 50)

                            elif event.key == pygame.K_r:
                                game.reset_game()
                                last_milestone = 0
                                submitted = False

            game.update(delta_time)

            current_milestone = (game.score // 1000) * 1000

            if current_milestone > last_milestone:
                sounds.play_milestone()
                last_milestone = current_milestone

            if game.score > self.high_score:
                self.high_score = game.score

            if game.state == "GAME_OVER" and not submitted:
                submitted = True

                updated_pb = api.submit_score(
                    self.token,
                    self.high_score
                )

                self.high_score = updated_pb

                if self.stay_signed_in:
                    auth.save_token(
                        self.username,
                        self.token,
                        self.high_score
                    )

            game_area = win.subsurface(
                pygame.Rect(
                    TOP_LEFT_X,
                    TOP_LEFT_Y,
                    SCREEN_WIDTH,
                    SCREEN_HEIGHT
                )
            )

            game.draw_board(game_area)

            if game.state == "PLAYING" and not game.paused:
                game.draw_piece(game_area, game.current_piece)

            game.draw_ui(game_area)
            game.draw_overlays(game_area)

            pygame.display.update()

        pygame.key.set_repeat(0, 0)


if __name__ == "__main__":
    app = GameApp()
    app.run()
    pygame.quit()


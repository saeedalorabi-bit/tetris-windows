import pygame
import os

pygame.mixer.init()

def load_sound(name):
    if os.path.exists(name):
        return pygame.mixer.Sound(name)
    return pygame.mixer.Sound(buffer=bytearray([128] * 1000))

sfx_move = load_sound("move.wav")
sfx_clear = load_sound("clear.wav")
sfx_milestone = load_sound("milestone.wav")

def play_milestone():
    sfx_milestone.play()

def play_move():
    sfx_move.play()

def play_clear():
    sfx_clear.play()
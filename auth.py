import json

import os

import re

from settings import TOKEN_FILE


def save_token(username, token, high_score):

    with open(TOKEN_FILE, "w") as f:

        json.dump({"username": username, "token": token, "high_score": high_score}, f)


def load_token():

    if os.path.exists(TOKEN_FILE):

        try:

            with open(TOKEN_FILE, "r") as f:

                return json.load(f)

        except:

            return None

    return None


def clear_token():

    if os.path.exists(TOKEN_FILE):

        os.remove(TOKEN_FILE)


def local_profanity_check(username):

    if not username or len(username) > 20 or not username.isascii():

        return "Username format is invalid or too long."

    bad_words = ['nigger', 'bitch', 'dick', 'fuck', 'ass', 'cunt', 'shit', 'cock', 'pussy']

    char_map = {'1': 'i', '0': 'o', '@': 'a', '$': 's', '3': 'e', '4': 'a', '5': 's', '7': 't'}

    norm = username.lower()

    for k, v in char_map.items():

        norm = norm.replace(k, v)

    # Split the username into actual words.
    # This prevents "ass" from blocking words like "gasso", "class", and "pass".
    words = re.findall(r'[a-z]+', norm)

    if any(word in bad_words for word in words):

        return "Username contains prohibited words."

    return ""
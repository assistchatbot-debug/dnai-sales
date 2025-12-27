#!/usr/bin/env python3
with open('bot/handlers.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    # Show lines around 76
    for i in range(70, 85):
        if i < len(lines):
            print(f"{i+1}: {lines[i]}", end='')

#!/usr/bin/env python3
with open('bot/handlers.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    # Show voice handler lines 151-200
    for i in range(150, 200):
        if i < len(lines):
            print(f"{i+1}: {lines[i]}", end='')

#!/usr/bin/env python3
with open('bot/handlers.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    # Show lines 360-380
    for i in range(359, 380):
        if i < len(lines):
            print(f"{i+1}: {lines[i]}", end='')

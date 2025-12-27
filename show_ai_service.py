#!/usr/bin/env python3
with open('backend/services/ai_service.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    # Show lines 20-50
    for i in range(19, 50):
        if i < len(lines):
            print(f"{i+1}: {lines[i]}", end='')

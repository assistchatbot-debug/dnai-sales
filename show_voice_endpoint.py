#!/usr/bin/env python3
with open('backend/routers/sales_agent.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    # Show lines 761-800
    for i in range(760, 800):
        if i < len(lines):
            print(f"{i+1}: {lines[i]}", end='')

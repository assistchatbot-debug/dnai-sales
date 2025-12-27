#!/usr/bin/env python3
with open('backend/routers/sales_agent.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    # Show lines 885-910
    for i in range(884, min(910, len(lines))):
        print(f"{i+1}: {lines[i]}", end='')

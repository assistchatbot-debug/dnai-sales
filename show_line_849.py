#!/usr/bin/env python3
with open('backend/routers/sales_agent.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i in range(845, 855):
        if i < len(lines):
            print(f"{i+1}: {lines[i]}", end='')

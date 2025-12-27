#!/usr/bin/env python3
with open('bot/handlers.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    
print("=== Проверка передачи language в /chat ===\n")

# Check line 25
print("1. Строка 25:")
for i in range(24, 35):
    if i < len(lines):
        print(f"{i+1}: {lines[i]}", end='')

print("\n2. Строка 132:")
for i in range(131, 142):
    if i < len(lines):
        print(f"{i+1}: {lines[i]}", end='')

print("\n3. Строка 300:")
for i in range(299, 310):
    if i < len(lines):
        print(f"{i+1}: {lines[i]}", end='')

print("\n4. Строка 669:")
for i in range(668, 679):
    if i < len(lines):
        print(f"{i+1}: {lines[i]}", end='')

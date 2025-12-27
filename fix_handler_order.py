#!/usr/bin/env python3
"""Move FSM handlers before generic handler"""

with open('bot/handlers.py', 'r') as f:
    lines = f.readlines()

print("🔧 Reordering handlers...")

# Find FSM handlers (around lines 465-530)
fsm_start = None
fsm_end = None
for i, line in enumerate(lines):
    if '@router.message(ManagerFlow.entering_channel_name)' in line:
        fsm_start = i
    if fsm_start and '@router.callback_query' in line:
        fsm_end = i
        break

if not fsm_start or not fsm_end:
    print("❌ FSM handlers not found!")
    exit(1)

# Extract FSM block
fsm_block = lines[fsm_start:fsm_end]
print(f"✅ Found FSM handlers: lines {fsm_start+1}-{fsm_end}")

# Remove FSM block
lines[fsm_start:fsm_end] = []

# Find generic handle_text (now around line 400)
generic_line = None
for i, line in enumerate(lines):
    if '@router.message()' in line and 'async def handle_text' in lines[i+1]:
        generic_line = i
        break

if not generic_line:
    print("❌ Generic handler not found!")
    exit(1)

# Insert FSM block BEFORE generic handler
lines[generic_line:generic_line] = ['\n'] + fsm_block + ['\n']
print(f"✅ Moved FSM handlers before generic handler (line {generic_line+1})")

# Remove the state check from handle_text (no longer needed)
new_lines = []
skip_lines = 0
for i, line in enumerate(lines):
    if skip_lines > 0:
        skip_lines -= 1
        continue
    
    if 'Skip if user is in FSM state' in line:
        # Skip next 3 lines (comment + check + return)
        skip_lines = 3
        continue
    
    new_lines.append(line)

print("✅ Removed state check from handle_text")

with open('bot/handlers.py', 'w') as f:
    f.writelines(new_lines)

print("\n✅ Done!")

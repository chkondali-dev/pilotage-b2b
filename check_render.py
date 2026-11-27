#!/usr/bin/env python3
import re

filepath = r'C:\Users\hachk\pilotage_b2b\ui\tabs\tab0_executive.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Check if the old render function exists
if "k2.metric(f'Factures'" in content:
    print('Found old render function - proceeding with replacement')
else:
    print('Old render function not found - checking current state')
    # Show first 200 chars
    print(content[:200])
with open('.env', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        if 'ANTHROPIC' in line:
            print(f"Line {i}: {line.strip()}")
            if '=' in line:
                key = line.split('=', 1)[1].strip()
                print(f"Key length: {len(key)}")
                print(f"First 30 chars: {key[:30]}")

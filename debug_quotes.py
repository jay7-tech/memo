
path = r"C:\Users\JAYADEEP GOWDA K B\Desktop\MEMO\core\personality.py"
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

count = 0
for i, line in enumerate(lines):
    quotes = line.count('"""')
    if quotes > 0:
        print(f"Line {i+1}: {quotes} quotes | Content: {line.strip()}")
        count += quotes

print(f"Total triple-quotes: {count}")

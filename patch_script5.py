import re

with open("specs/cortex-api.yaml", "r") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "翻译 /" in line:
        lines[i] = line.replace("翻译 / ", "")

with open("specs/cortex-api.yaml", "w") as f:
    f.writelines(lines)

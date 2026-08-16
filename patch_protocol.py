import re

file_path = "packages/domain/src/cortex_domain/models.py"

with open(file_path, "r") as f:
    content = f.read()

# Let's check if there is a repository protocol

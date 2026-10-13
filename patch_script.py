with open("specs/cortex-api.yaml", "r") as f:
    content = f.read()

new_content = content.replace(
    "  summary: 面向数据解析、存储、知识构建、效果评测与数据合成的厂商中立 API。 / Vendor-neutral APIs for parse,\n    storage, knowledge, evaluation, and synthesis.",
    "  summary: Vendor-neutral APIs for parse, storage, knowledge, evaluation, and synthesis. / 面向数据解析、存储、知识构建、效果评测与数据合成的厂商中立 API。"
)

with open("specs/cortex-api.yaml", "w") as f:
    f.write(new_content)

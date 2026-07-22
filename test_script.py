from cortex_parse.adapters.docling import DoclingParseEngine

print(DoclingParseEngine({"enabled": True}).descriptor.status)

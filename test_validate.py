from scripts.ci.validate_yaml import _validate_openapi

try:
    _validate_openapi()
    print("SUCCESS")
except Exception as e:
    print("FAILED", e)

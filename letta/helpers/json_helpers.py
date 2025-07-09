import json
from datetime import datetime


def json_loads(data):
    return json.loads(data, strict=False)


def json_dumps(data, indent=2):
    def safe_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, bytes):
            # Try to decode bytes to string, fallback to base64 if not UTF-8
            try:
                return obj.decode('utf-8')
            except UnicodeDecodeError:
                import base64
                return base64.b64encode(obj).decode('ascii')
        raise TypeError(f"Type {type(obj)} not serializable")

    return json.dumps(data, indent=indent, default=safe_serializer, ensure_ascii=False)

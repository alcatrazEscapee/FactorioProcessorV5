from utils import JsonObject

import zlib
import json
import base64


def decode_blueprint_string(blueprint: str) -> JsonObject:
    version_char = blueprint[0]
    if version_char == '0':
        compressed = base64.b64decode(bytes(blueprint[1:], 'UTF-8'))
        text = zlib.decompress(compressed)
        return json.loads(text)
    else:
        raise ValueError('Unknown version byte %s' % version_char)


def encode_blueprint_string(blueprint: JsonObject, version_char: str = '0') -> str:
    if version_char == '0':
        text = json.dumps(blueprint)
        compressed = zlib.compress(bytes(text, 'UTF-8'))
        return '0' + base64.b64encode(compressed).decode('UTF-8')
    else:
        raise ValueError('Unknown version byte %s' % version_char)

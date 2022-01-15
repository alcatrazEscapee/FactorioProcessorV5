from json import loads, dumps
from zlib import decompress, compress
from base64 import b64decode, b64encode
from typing import Dict, Any


def decode_blueprint_string(blueprint: str) -> Dict[str, Any]:
    version_char = blueprint[0]
    if version_char == '0':
        base64 = b64decode(bytes(blueprint[1:], 'UTF-8'))
        json = decompress(base64)
        return loads(json)
    else:
        raise ValueError('Unknown version byte %s' % version_char)


def encode_blueprint_string(json: Dict[str, Any], version_char: str = '0') -> str:
    if version_char == '0':
        text = dumps(json)
        compressed = compress(bytes(text, 'UTF-8'))
        return '0' + b64encode(compressed).decode('UTF-8')
    else:
        raise ValueError('Unknown version byte %s' % version_char)

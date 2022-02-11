from utils import JsonObject

import zlib
import json
import base64
import argparse


def read_command_line_args():
    parser = argparse.ArgumentParser(description='A tool for manipulating blueprints')
    return parser.parse_args()


def main(args: argparse.Namespace):
    with open('../assets/60kb_rom.blueprint', 'r', encoding='utf-8') as f:
        bp = f.read()

    js = decode_blueprint_string(bp)

    with open('../assets/60kb_rom.blueprint.json', 'w', encoding='utf-8') as f:
        json.dump(js, f, indent=2)


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


if __name__ == '__main__':
    main(read_command_line_args())

#!/usr/bin/env python3
import json
import sys
import os

# Ensure project root is on sys.path when running from scripts/
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from utils.image_analyzer import analyze_images, build_vision_model


def main():
    # Default to a Wikimedia Commons DFD example (redirects to raw file)
    default_url = 'https://commons.wikimedia.org/wiki/Special:FilePath/Data-flow-diagram-example.svg'
    image_url = sys.argv[1] if len(sys.argv) > 1 else default_url

    images = [{
        'alt': 'DFD example',
        'title': 'Data Flow Diagram',
        'abs_url': image_url,
    }]

    # Show which provider will be used
    vm = build_vision_model(options=None)
    print(json.dumps({
        'provider': vm.__class__.__name__,
        'base_url': getattr(vm, 'base_url', None),
        'model': getattr(vm, 'model', None),
        # avoid printing API key
    }, ensure_ascii=False))

    results = analyze_images(images, base_url=None, options=None)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
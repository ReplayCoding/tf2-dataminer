#!/usr/bin/env python3

import argparse
from pathlib import Path
import sys
from dataminer.build import process_dir, load_config

def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", required=True)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)

    args = parser.parse_args()

    load_config(args.config)
    process_dir(args.input, args.output)

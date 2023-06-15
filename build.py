from file import File
from processor import PROCESSORS, Processor
from extractor import EXTRACTORS

from pathlib import Path
from fnmatch import fnmatchcase
import os
import yaml

CONFIG = {}
with open("config.yaml", "rb") as fd:
    CONFIG = yaml.safe_load(fd)

def process_dir(input_path: Path, output_path: Path):
    output_root = output_path.absolute()

    if not output_root.exists():
        output_root.mkdir(parents=True)

    instantiated_processors: list[Processor] = []

    for proc in PROCESSORS:
        proc = proc(output_root)

        proc.pre_process()
        instantiated_processors.append(proc)

    def run_processors_on_file(file_info: File):
        for proc in instantiated_processors:
            path_to_match = file_info.path.relative_to(file_info.input_root).as_posix()

            pats = CONFIG["processors"][proc.name]["filters"]
            for pat in pats:
                if fnmatchcase(path_to_match, pat):
                    # print(path_to_match, pat, proc.name)
                    proc.run_processor(file_info)

    for root, _, files in os.walk(input_path):
        for path in files:
            file_info = File(input_root=input_path.absolute(), path=Path(os.path.join(root, path)).absolute())

            run_processors_on_file(file_info)

            for ex in EXTRACTORS:
                path_to_match = file_info.path.relative_to(file_info.input_root).as_posix()

                pats = CONFIG["extractors"][ex.name]["filters"]
                for pat in pats:
                    if fnmatchcase(path_to_match, pat):
                        # print(path_to_match, pat, ex.name)
                        for f in ex.get_files(file_info):
                            run_processors_on_file(f)

    for proc in instantiated_processors:
        print(proc.artifact_mappings)

process_dir(Path("tf2"), Path("out"))
process_dir(Path("tf2_prev"), Path("out2"))

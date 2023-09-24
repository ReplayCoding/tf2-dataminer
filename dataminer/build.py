from dataminer.file import File
from dataminer.processor import PROCESSORS, Processor
from dataminer.extractor import EXTRACTORS

from pathlib import Path
from fnmatch import fnmatchcase
import os
import yaml

CONFIG = {}


def load_config(path: Path):
    global CONFIG
    with open(path, "rb") as fd:
        CONFIG = yaml.safe_load(fd)


def process_dir(input_path: Path, output_path: Path):
    output_root = output_path.absolute()

    if not output_root.exists():
        output_root.mkdir(parents=True)

    instantiated_processors: list[Processor] = []

    proc_dict = {}
    for proc in PROCESSORS:
        proc_dict[proc.name] = proc

    for proc_config in CONFIG["processors"]:
        name = proc_config["name"]
        proc = proc_dict[name](output_root, proc_config)

        proc.pre_process()
        instantiated_processors.append(proc)

    def run_processors_on_file(file_info: File):
        for proc in instantiated_processors:
            path_to_match = file_info.path.relative_to(file_info.input_root).as_posix()

            pats = proc.config["filters"]
            for pat in pats:
                if fnmatchcase(path_to_match, pat):
                    # print(path_to_match, pat, proc.name)
                    try:
                        proc.run_processor(file_info)
                    except Exception as e:
                        print(
                            f'ERROR while running processor "{proc.name}" on file "{file_info.path}"'
                        )
                        raise e

    for root, _, files in os.walk(input_path):
        for path in files:
            file_info = File(
                input_root=input_path.absolute(),
                path=Path(os.path.join(root, path)).absolute(),
            )

            run_processors_on_file(file_info)

            for ex in EXTRACTORS:
                path_to_match = file_info.path.relative_to(
                    file_info.input_root
                ).as_posix()

                pats = CONFIG["extractors"][ex.name]["filters"]
                for pat in pats:
                    if fnmatchcase(path_to_match, pat):
                        # print(path_to_match, pat, ex.name)
                        for f in ex.get_files(file_info):
                            run_processors_on_file(f)

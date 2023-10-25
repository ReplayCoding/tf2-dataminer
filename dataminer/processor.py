from dataminer.file import File

from pathlib import Path
import re
import subprocess
import typing
import shutil
from dataminer import vpk


class Processor:
    name: str

    config: dict[str, str]

    def __init__(self, output_root: Path, config: dict[str, str]):
        self.output_root = output_root
        self.config = config

    # Public interface to process_file
    def run_processor(self, file: File):
        self.process_file(file)

    # TODO: Maybe rename this?
    def pre_process(self):
        pass

    def process_file(self, file: File):
        pass

    def run_command_for_file(
        self,
        command,
        file: File,
        output_suffix=".txt",
        no_processor_name=False,
        replace_processor_name=None,
        **kwargs,
    ):
        if type(command) != list:
            command = [command]

        command[0] = shutil.which(command[0])

        proc = subprocess.run(
            command + [file.obtain_real_file_path()], capture_output=True, **kwargs
        )

        # TODO: Proper Error handling
        if proc.returncode == 0:
            with self.create_output_file_for(
                file,
                output_suffix=output_suffix,
                no_processor_name=no_processor_name,
                replace_processor_name=replace_processor_name,
            ) as output:
                if "line_discard_filter" in self.config:
                    r = re.compile(self.config["line_discard_filter"])
                    for line in proc.stdout.decode("utf8").split("\n"):
                        line = line.strip()
                        if r.search(line) == None:
                            output.write((line + "\n").encode("utf8"))
                else:
                    output.write(proc.stdout)
        else:
            print("ERROR:", file.path, proc.returncode, self.name)
            print(proc.stdout.decode("utf8"))
            print(proc.stderr.decode("utf8"))

    def create_output_file_for(
        self, file: File, output_suffix=".txt",
        no_processor_name=False, replace_processor_name=None,
    ):
        path = file.path
        final_dir = self.output_root.joinpath(path.parent.relative_to(file.input_root))
        final_dir.mkdir(parents=True, exist_ok=True)

        final_fname = f"{path.stem}_{replace_processor_name or self.name}{output_suffix}"
        if no_processor_name:
            final_fname = f"{path.stem}{output_suffix}"
        final_path: Path = final_dir.joinpath(final_fname)

        return final_path.open("wb")


class VtableProcessor(Processor):
    name = "vtables"

    def process_file(self, file: File):
        self.run_command_for_file(self.config["bin_path"], file)


class StringProcessor(Processor):
    name = "strings"

    def process_file(self, file: File):
        self.run_command_for_file("strings", file)


class SymbolsProcessor(Processor):
    name = "symbols"

    def process_file(self, file: File):
        self.run_command_for_file(["nm", "--just-symbol-name"], file)


class NetvarProcessor(Processor):
    name = "netvars"

    def process_file(self, file: File):
        assert file.is_real

        path = file.path
        env = {
            "LD_LIBRARY_PATH": f"{path.parent}:{path.parent.parent.parent.joinpath('bin')}"
        }

        self.run_command_for_file(self.config["bin_path"], file, env=env)


class ConvarProcessor(Processor):
    name = "convars"

    def process_file(self, file: File):
        assert file.is_real

        path = file.path
        env = {
            "LD_LIBRARY_PATH": f"{path.parent}:{path.parent.parent.parent.joinpath('bin')}"
        }

        self.run_command_for_file(self.config["bin_path"], file, env=env)


class ProtobufProcessor(Processor):
    name = "protobufs"

    def pre_process(self):
        self.protobuf_dir = self.output_root.joinpath("Protobufs")

        self.protobuf_dir.mkdir()

    def process_file(self, file: File):
        out_path = self.protobuf_dir.joinpath(file.path.stem)
        proc = subprocess.run(
            [
                shutil.which(self.config["bin_path"]),
                file.obtain_real_file_path(),
                out_path,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # TODO: Proper Error handling
        if proc.returncode != 0:
            print("ERROR:", file, proc.returncode, self.name)


class BspEntitiesProcessor(Processor):
    name = "bsp_entities"

    def process_file(self, file: File):
        self.run_command_for_file(["bspinfo", "entities"], file, replace_processor_name="entities")

class BspFileListingProcessor(Processor):
    name = "bsp_listing"

    def process_file(self, file: File):
        self.run_command_for_file(["bspinfo", "files"], file, replace_processor_name="listing")

class VpkProcessor(Processor):
    name = "vpk"

    def process_file(self, file: File):
        assert file.is_real

        pak = vpk.open(file.path)

        with self.create_output_file_for(file, no_processor_name=True) as fd:
            entries = []
            for name, meta in pak.read_index_iter():
                # WTF
                crc = meta[1]
                size = meta[5]

                entries.append((name, crc, size))

            # Sort by name
            entries.sort(key = lambda e: e[0])
            
            for (name, crc, size) in entries:
                line = "{} {:08x} {}\n".format(name, crc, size)
                fd.write(line.encode("utf8"))


class CopyProcessor(Processor):
    name = "copy"

    def process_file(self, file: File):
        do_raw_copy = True

        path = file.path
        final_dir = self.output_root.joinpath(path.parent.relative_to(file.input_root))
        final_dir.mkdir(parents=True, exist_ok=True)

        output_file = final_dir.joinpath(file.path.name)
        
        with file.open() as inp_fd, output_file.open(
            "wb"
        ) as out_fd:
            if self.config["convert_utf8"]:
                do_raw_copy = False

                bom = inp_fd.read(4)
                output_encoding = "utf-8"
                # Number of unused bytes from the BOM, since we always read 4 bytes.
                n_copy_back = 0

                # Default assumed encoding is utf-8
                encoding = "utf-8"
                if bom[0:4] == b"\x00\x00\xFE\xFF":
                    encoding = "utf-32be"
                elif bom[0:4] == b"\xFF\xFE\x00\x00":
                    encoding = "utf-32le"
                elif bom[0:2] == b"\xFE\xFF":
                    encoding = "utf-16be"
                    n_copy_back = 2
                elif bom[0:2] == b"\xFF\xFE":
                    encoding = "utf-16le"
                    n_copy_back = 2

                data = bom[-n_copy_back:] + inp_fd.read()

                # If decode fails, fallback to raw copy
                try:
                    decoded = data.decode(encoding)
                    out_fd.write(decoded.encode(output_encoding))
                except:
                    do_raw_copy = True

            if do_raw_copy:
                inp_fd.seek(0)
                out_fd.seek(0)
                out_fd.truncate(0)

                shutil.copyfileobj(inp_fd, out_fd)


class IceProcessor(Processor):
    name = "ice"

    def process_file(self, file: File):
        self.run_command_for_file(
            [self.config["bin_path"], "-d", "-k", self.config["ice_key"]],
            file,
            no_processor_name=True,
        )


PROCESSORS: list[typing.Type[Processor]] = [
    CopyProcessor,
    NetvarProcessor,
    ConvarProcessor,
    VtableProcessor,
    StringProcessor,
    SymbolsProcessor,
    ProtobufProcessor,
    BspEntitiesProcessor,
    BspFileListingProcessor,
    VpkProcessor,
    IceProcessor,
]

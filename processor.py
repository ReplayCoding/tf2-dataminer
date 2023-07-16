from file import File

from pathlib import Path
import subprocess
import typing
import shutil
import bsp_tool
import vpk

class Processor:
    name: str

    artifact_mappings: dict[Path, list[Path]]
    config: dict[str, str]

    def __init__(self, output_root: Path, config: dict[str, str]):
        self.output_root = output_root
        self.artifact_mappings = {}
        self.config = config

    # Public interface to process_file
    def run_processor(self, file: File):
        self.process_file(file)

    def add_artifact(self, parent: File, artifact: Path):
        # print(f"Adding artifact for {parent.path} ({artifact})")

        if not (parent.path in self.artifact_mappings):
            self.artifact_mappings[parent.path] = []

        self.artifact_mappings[parent.path].append(artifact)

    # TODO: Maybe rename this?
    def pre_process(self):
        pass

    def process_file(self, file: File):
        pass

    def run_command_for_file(
        self, command, file: File, output_suffix=".txt", **kwargs
    ):
        if type(command) != list:
            command = [command]

        proc = subprocess.run(command + [file.obtain_real_file_path()], capture_output=True, **kwargs)

        # TODO: Proper Error handling
        if proc.returncode == 0:
            with self.create_output_file_for(
                file, output_suffix=output_suffix
            ) as output:
                output.write(proc.stdout)
        else:
            print("ERROR:", file.path, proc.returncode, self.name)
            print(proc.stdout.decode("utf8"))
            print(proc.stderr.decode("utf8"))

    def create_output_file_for(self, file: File, output_suffix=".txt"):
        path = file.path
        final_dir = self.output_root.joinpath(
            path.parent.relative_to(file.input_root)
        )
        final_dir.mkdir(parents=True, exist_ok=True)

        final_path: Path = final_dir.joinpath(f"{path.stem}_{self.name}{output_suffix}")

        self.add_artifact(file, final_path)
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
        assert(file.is_real)

        path = file.path
        env = {
            "LD_LIBRARY_PATH": f"{path.parent}:{path.parent.parent.parent.joinpath('bin')}"
        }

        self.run_command_for_file("./nvdumper", file, env=env)


class ProtobufProcessor(Processor):
    name = "protobufs"

    def pre_process(self):
        self.protobuf_dir = self.output_root.joinpath("Protobufs")

        self.protobuf_dir.mkdir()

    def process_file(self, file: File):
        out_path = self.protobuf_dir.joinpath(file.path.stem)
        proc = subprocess.run(
            [self.config["bin_path"], file.obtain_real_file_path(), out_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # TODO: Proper Error handling
        if proc.returncode != 0:
            print("ERROR:", file, proc.returncode, self.name)
        else:
            if out_path.exists():
                self.add_artifact(file, out_path)


class BspProcessor(Processor):
    name = "bsp"

    def process_file(self, file: File):
        bsp = bsp_tool.load_bsp(file.obtain_real_file_path().as_posix(), bsp_tool.branches.valve.orange_box)

        output = [
            f"BSP Version: {bsp.bsp_version}",
            f"Revision: {bsp.revision}"
        ]

        for lump in bsp.branch.LUMP:
            lump = lump.name
            if lump not in bsp.headers:
                continue

            lump_header = bsp.headers[lump]

            # BSP info extraction already takes quite a while, this takes even more time :(
            # Maybe multiprocess/thread processors?
            # crc = "error"
            # try:
            #     lump_content = bsp.lump_as_bytes(lump)
            #     crc = "{:08x}".format(zlib.crc32(lump_content))
            # except Exception as e:
            #     pass
            output.append(f"{lump} (v{lump_header.version}): size = {lump_header.length}")

        with self.create_output_file_for(file) as fd:
            fd.write("\n".join(output).encode("utf8"))


class VpkProcessor(Processor):
    name = "vpk"

    def process_file(self, file: File):
        assert(file.is_real)

        pak = vpk.open(file.path)

        with self.create_output_file_for(file) as fd:
            for name, meta in pak.read_index_iter():
                # WTF
                crc = meta[1]
                size = meta[5]

                line = "{} {:08x} {}\n".format(name, crc, size)
                fd.write(line.encode("utf8"))

class CopyProcessor(Processor):
    name = "copy"

    def process_file(self, file: File):
        path = file.path
        final_dir = self.output_root.joinpath(
            path.parent.relative_to(file.input_root)
        )
        final_dir.mkdir(parents=True, exist_ok=True)

        output_file = final_dir.joinpath(file.path.name)
        self.add_artifact(file, output_file)
        shutil.copyfile(file.obtain_real_file_path(), output_file)

class IceProcessor(Processor):
    name = "ice"

    def process_file(self, file: File):
        self.run_command_for_file([self.config["bin_path"], "-d", "-k", self.config["ice_key"]], file)

# Needs binja to work
# import ctypes
# from binaryninja import open_view
#
# class BinexportProcessor(Processor):
#     name = "binexport"
#     binexport_mod = ctypes.CDLL("binexport12_binaryninja.so")
#
#     def process_file(self, file: File):
#
#         options = { "analysis.mode": "basic" } # Is this enough?
#         with open_view(file.obtain_real_file_path().as_posix(), options = options) as view:
#             # TODO: Merge with copy processor code & create_output_file_for
#             path = file.path
#             final_dir = self.output_root.joinpath(
#                 path.parent.relative_to(file.input_root)
#             )
#             final_dir.mkdir(parents=True, exist_ok=True)
#             out_path = final_dir.joinpath(f"{file.path.stem}.BinExport")
#
#             self.add_artifact(file, out_path)
#             self.binexport_mod.BEExportFile(out_path.as_posix().encode("ascii"), view.handle)

PROCESSORS: list[typing.Type[Processor]] = [
    CopyProcessor,
    # NetvarProcessor,
    VtableProcessor,
    StringProcessor,
    SymbolsProcessor,
    ProtobufProcessor,
    BspProcessor,
    VpkProcessor,
    IceProcessor,
    # BinexportProcessor,
]

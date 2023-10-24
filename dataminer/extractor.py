from os import walk
from dataminer.file import BSPPakFile, File, VPKFile
from dataminer import vpk

import typing
import zipfile


class Extractor:
    name: str

    @classmethod
    def get_files(cls, input_file: File) -> typing.Iterable[File]:
        return []


class VpkExtractor(Extractor):
    name = "vpk"

    @classmethod
    def get_files(cls, input_file: File):
        # print("vpk extract", input_file.path)

        # without as_posix, everything explodes :)
        try:
            pak = vpk.open(input_file.obtain_real_file_path().as_posix())
        except Exception as e:
            print("Couldn't open vpk:", e)
            return []

        for path, metadata in pak.read_index_iter():
            try:
                vpkfile = pak.get_vpkfile_instance(path, metadata)
            except Exception as e:
                print("Couldn't read vpk:", e)
                return []

            vpk_relpath = input_file.obtain_real_file_path().relative_to(
                input_file.input_root
            )

            yield VPKFile(
                vpkfile, vpk_relpath.parent.joinpath(vpk_relpath.stem).joinpath(path)
            )

class BspExtractor(Extractor):
    name = "bsp"

    @classmethod
    def get_files(cls, input_file: File):
        bsp = None

        try:
            bsp = zipfile.ZipFile(input_file.obtain_real_file_path())
        except Exception as e:
            print("Couldn't open bsp (probably no pakfile):", e)
            return []

        for info in bsp.infolist():
            f = bsp.open(info)

            extracted_relpath = input_file.obtain_real_file_path().relative_to(input_file.input_root)

            yield BSPPakFile(f, info.file_size, extracted_relpath.parent.joinpath(extracted_relpath.stem).joinpath(info.filename))


EXTRACTORS: list[typing.Type[Extractor]] = [VpkExtractor, BspExtractor]

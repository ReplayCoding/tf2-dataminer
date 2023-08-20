from dataminer.file import File, VPKFile

import typing
import vpk

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

            vpk_relpath = input_file.obtain_real_file_path().relative_to(input_file.input_root)

            yield VPKFile(vpkfile, vpk_relpath.parent.joinpath(vpk_relpath.stem).joinpath(path))


EXTRACTORS: list[typing.Type[Extractor]] = [
    VpkExtractor
]


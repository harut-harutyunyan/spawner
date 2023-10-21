import os
import re


import pyseq

# env
os.environ["MY_WORK_ROOT"] = "/Users/harut/Documents/harut/prj"
os.environ["MY_PROJECT_ABBR"] = "trainvfx"
os.environ["MY_SEQUENCE"] = "int010"
os.environ["MY_SHOT"] = "int010_0020"
os.environ["MY_TASK_NAME"] = "scan"

# example filepath
filepath = "/Users/harut/Documents/harut/prj/trainvfx/int010/int010_0020/scan/fg01/v001/int010_0020_fg01.%04d.jpg"
# example filelist
# file_list = ['env:MY_WORK_ROOT', 'env:MY_PROJECT_ABBR', 'env:MY_SEQUENCE', 'env:MY_SHOT', 'scan', 'fg01', 'v001', 'int010_0020_fg01.1001.jpg']
file_list = ['env:MY_WORK_ROOT', 'env:MY_PROJECT_ABBR', 're:.*', 're:.*', 'scan', 'fg01', 'v:all', r're:.*']


WORK_ROOT = os.getenv("MY_WORK_ROOT", "")
PROJECT_ABBR = os.getenv("MY_PROJECT_ABBR", "")

class PathsHandler(object):


    SEQ = True
    FILE_FOLMATS = [
                    ".jpg",
                    ".png",
                    ".exr",
                    ".tif",
                    ".tiff",
                    ".dpx",
                    ".hdr",
                    ".targa",
                    ".cin",
                    ".abc",
                    ".fbx",
                    ".obj",
                    ".gizmo",
                    ".nk",
                    ]

    @classmethod
    def _path_split(cls, filepath):
        file_list = []

        while True:
            filepath, folder = os.path.split(filepath)
            if folder:
                file_list.insert(0, folder)
            else:
                break

        return file_list

    @classmethod
    def _handle_file_name(cls, file_name):

        name, ext = os.path.splitext(file_name)

        if name.endswith("#") or re.search(r'.*%[0-9]+d$', name):
            return r"re:\w+[\._]\d+\.{}$".format(ext[1:])

        return r"re:.*\.{}$".format(ext[1:])

    @classmethod
    def _split(cls, filepath, guess=True):
        file_list = cls._path_split(filepath)
        file_list = file_list[file_list.index(PROJECT_ABBR)+1:]

        file_list = ['env:MY_WORK_ROOT', 'env:MY_PROJECT_ABBR']+file_list

        for string in file_list:
            match = re.search(r'v(\d+)', string)
            if match:
                version = str(match.group())
                if version in file_list:
                    file_list[file_list.index(version)] = "v:latest"

        file_list[-1] = cls._handle_file_name(file_list[-1])

        if guess:
            file_list[2] = "env:MY_SEQUENCE"
            file_list[3] = "env:MY_SHOT"
            file_list[4] = "env:MY_TASK_NAME"

        return file_list

    @classmethod
    def _get_version(cls, version_list, index=0):
        pattern = r'v(\d+)'

        all_versions = [0]

        for version in version_list:
            match = re.search(pattern, version)
            if match:
                version_number = int(match.group(1))
                all_versions.append(version_number)

        return sorted(all_versions, reverse=True)[index%len(all_versions)]

    @classmethod
    def _handle_env(cls, string):
        return [os.getenv(string[4:], "")]

    @classmethod
    def _handle_regex(cls, filepath, string):
        pattern = string[3:]
        match_list = []

        if not os.path.isdir(filepath):
            return []

        for item in os.listdir(filepath):
            if re.search(pattern, item):
                match_list.append(item)

        return match_list

    @classmethod
    def _handle_version(cls, filepath, string):
        ver = string[2:]
        if ver.isdigit():
            return cls._handle_regex(filepath, r"re:^v.*{}$".format(ver))
        elif ver=="all":
            return cls._handle_regex(filepath, r"re:v(\d+)")
        elif ver=="latest":
            latest_version = cls._get_version(os.listdir(filepath))
            return cls._handle_version(filepath, "v:{}".format(latest_version))
        elif ver.startswith("-") and ver[1:].isdigit():
            version = cls._get_version(os.listdir(filepath), int(ver[1:]))
            return cls._handle_version(filepath, "v:{}".format(version))
        else:
            return []

    @classmethod
    def _handle_folder_string(cls, current_path, string):
        if string.startswith("env:"):
            folder_list = cls._handle_env(string)
        elif string.startswith("re:"):
            folder_list = cls._handle_regex(current_path, string)
        elif string.startswith("v:"):
            folder_list = cls._handle_version(current_path, string)
        else:
            folder_list = [os.path.join(current_path, string)]

        return folder_list

    @classmethod
    def _construct_file_names(cls, current_path, string):
        results =[]

        folder_list = cls._handle_folder_string(current_path, string)
        for folder in folder_list:
            new_path = os.path.join(current_path, folder)
            if os.path.exists(new_path):
                results.append(new_path)

        return results

    @classmethod
    def _construct_file_paths(cls, string_list, current_path=""):
        if not string_list:
            return [current_path]

        string, *tail = string_list
        results = []

        for path in cls._construct_file_names(current_path, string):
            results.extend(cls._construct_file_paths(tail, path))

        return results

    @classmethod
    def _pyseq_convert(cls, path_dict):
        if cls.SEQ:
            for i in path_dict.keys():
                path_dict[i] = pyseq.Sequence(path_dict[i])

        return path_dict

    @classmethod
    def construct_file_paths(cls, string_list):
        file_paths = list(set(cls._construct_file_paths(string_list)))
        path_dict = {}
        for path in file_paths:
            if not os.path.splitext(path)[1] in cls.FILE_FOLMATS:
                continue
            dirname = os.path.dirname(path)
            if not dirname in path_dict.keys():
                path_dict[dirname] = [path]
                continue
            path_dict[dirname].append(path)

        return cls._pyseq_convert(path_dict)

if __name__ == '__main__':

    file_list = PathsHandler._split(filepath)
    print(file_list)
    # PathsHandler.SEQ = False

    dd = PathsHandler.construct_file_paths(file_list)

    for i in dd.keys():
        print(dd[i])


"""Miscellaneous functions.

All code in this file should be purely functional.
"""

from subprocess import run, PIPE, CompletedProcess
from os.path import isdir, dirname, realpath
from os.path import join as getpath
from os import access, listdir, removedirs, stat, walk
from os import F_OK as file_exists
from os import makedirs as mkdir
from os import sep as root
from shutil import copytree, copy
from hashlib import sha256
from strict_hint import strict


@strict
def list_recursively(f: str, *filepath) -> list:
    """Get a list of all files in a folder and its subfolders.

    :return: list: Absolute paths of all files in the folder.
    """
    if not isdir(getpath(f, *filepath)):
        # If the specified file isn't a directory, just return that one file.
        return [getpath(f, *filepath)]
    return [
        getpath(dp, f) for dp, dn, fn in walk(
            getpath(f, *filepath)
        ) for f in fn
    ]


@strict
def hash_of_str(val: str) -> str:
    """Get the sha256 hash of a string."""
    return sha256(val.encode('ascii')).hexdigest()


@strict
def perms(f: str, *filepath) -> int:
    """Get the permissions of a file as an octal number.

    The last three digits of the octal value are what you would put in for
    a standard bash chmod bitfield input. For example, you may receive
    0o100644 which would equate to rw-r--r-- or 644.

    :type filepath: tuple of strings to be passed to os.path.join
    """
    if f != root and f[0] != '/':
        raise ValueError("Path must be specified as a full path.")
    return stat(getpath(f, *filepath)).st_mode


@strict
def hash_of_file(f: str, *filepath) -> str:
    """Get the sha256 hash of a file read by read_absolute."""
    return hash_of_str(read_absolute(f, *filepath))


@strict
def read_relative(*fname: str) -> str:
    """Get the contents of a file in the current directory.

    NOTE: this means relative to the directory containing the misc_functions.py
    file!!! That may not be the directory in which your source file lies!

    Path should be passed like with os.path.join:
    read_relative('path', 'to', 'file')
    """
    with open(getpath(dirname(realpath(__file__)), *fname)) as file:
        return file.read()


@strict
def read_absolute(f: str, *fname: str) -> str:
    """Get the contents of a file from an absolute path.

    Path should be passed like with os.path.join:
    read_absolute(os.sep, 'path', 'to', 'file')
    """
    with open(getpath(f, *fname)) as file:
        return file.read()


@strict
def runcmd(cmd: str) -> CompletedProcess:
    """Alias subprocess.run, with check, shell, stdin and stdout enabled."""
    return run(cmd, check=True, shell=True, stdout=PIPE, stdin=PIPE)


@strict
def check_isdir(filepath: str, src: str='') -> bool:
    """Check to make sure a particular filepath is a directory.

    Also check that it's not a file and create it if it doesn't already
    exist.

    If src is specified it must be a path to be recursively copied into the
    directory should it not exist or be empty.
    """
    if not isdir(filepath):
        if access(filepath, mode=file_exists):
            raise FileExistsError(
                "Goal directory %s exists as a file." % (filepath)
            )
        if src:
            if isdir(src):
                # recursively copy source dir.
                copytree(src, filepath)
                return True
        # The returns mean the else is implied.
        # src not specified, just make an empty dir.
        mkdir(filepath, mode=0o755)
        if src:
            # we already checked if it was a dir, so just copy a single file.
            copy(src, filepath)
        return True
    if not listdir(filepath) and src:
        # The directory is empty but a source file/directory was passed.
        if isdir(src):
            removedirs(filepath)
            copytree(src, filepath)
            return True
        # the src is just a single file, so copy it to the existing dir.
        copy(src, filepath)
        return True
    return False    # this should never be reached.


@strict
def get_parent_dir(name: str) -> str:
    """Retrieve the parent directory of a named instance."""
    return getpath(
        root,
        "usr",
        "share",
        "quick_deployments",
        "static",
        name
    )

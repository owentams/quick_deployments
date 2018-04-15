"""Miscellaneous functions.

All code in this file should be purely functional.
"""

from subprocess import run, PIPE
from subprocess import CompletedProcess
from os.path import isdir, dirname, realpath
from os.path import join as getpath
from os import access, listdir, removedirs, stat
from os import F_OK as file_exists
from os import makedirs as mkdir
from shutil import copytree, copy
from docker.errors import APIError
from hashlib import sha256
from typing import Tuple
from src.config import Config


def hash_of_str(val: str) -> str:
    """Get the sha256 hash of a string."""
    return sha256(val.encode('ascii')).hexdigest()


def perms(*filepath: Tuple[str, ...]) -> int:
    """

    :type filepath: tuple of strings to be passed to os.path.join
    """
    return stat(getpath(*filepath)).st_mode


def hash_of_file(*filepath: str) -> str:
    """Get the sha256 hash of a file read by read_absolute."""
    return hash_of_str(read_absolute(*filepath))


def read_relative(*fname: str) -> str:
    """Get the contents of a file in the current directory.

    Path should be passed like with os.path.join:
    read_relative('path', 'to', 'file')
    """
    with open(getpath(dirname(realpath(__file__)), *fname)) as file:
        return file.read()


def read_absolute(*fname: str) -> str:
    """Get the contents of a file from an absolute path.

    Path should be passed like with os.path.join:
    read_absolute(os.sep, 'path', 'to', 'file')
    """
    with open(getpath(*fname)) as file:
        return file.read()


def runcmd(cmd: str) -> CompletedProcess:
    """Alias subprocess.run, with check, shell, stdin and stdout enabled."""
    return run(cmd, check=True, shell=True, stdout=PIPE, stdin=PIPE)


def check_isdir(filepath: str, src: str = '') -> bool:
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


def check_for_image(tag: str, version: str) -> bool:
    """Check that an image is present by the tag/version strings."""
    all_tags = [
        [tag for tag in image.tags] for image in Config.client.images.list()
    ]
    if "%s:%s" % (tag, version) in all_tags:
        return True
    try:
        Config.client.images.pull("%s:%s" % (tag, version))
    except APIError:
        return False
    return True

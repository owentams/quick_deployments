from src import misc_functions
from os.path import dirname, realpath, join
from os import sep as root
from pytest import raises

test_string = """The Zen of Python, by Tim Peters

Beautiful is better than ugly.
Explicit is better than implicit.
Simple is better than complex.
Complex is better than complicated.
Flat is better than nested.
Sparse is better than dense.
Readability counts.
Special cases aren't special enough to break the rules.
Although practicality beats purity.
Errors should never pass silently.
Unless explicitly silenced.
In the face of ambiguity, refuse the temptation to guess.
There should be one-- and preferably only one --obvious way to do it.
Although that way may not be obvious at first unless you're Dutch.
Now is better than never.
Although never is often better than *right* now.
If the implementation is hard to explain, it's a bad idea.
If the implementation is easy to explain, it may be a good idea.
Namespaces are one honking great idea -- let's do more of those!
"""
thisdir = dirname(realpath(__file__))


class Test_ListRecursively:
    """Test that the list_recursively function works properly."""
    def test_for_single_file(self):
        """Test that passing a file returns a list of only that file."""
        assert misc_functions.list_recursively(
            thisdir, "test_document_folder", "test_string.txt"
        ) == [
            join(thisdir, "test_document_folder", "test_string.txt")
        ]

    def test_folder(self):
        """Test that passing the folder returns the right files."""
        assert misc_functions.list_recursively(
            thisdir, "test_document_folder"
        ) == [
            join(thisdir, 'test_document_folder', "test_string.txt"),
            join(
                thisdir,
                "test_document_folder",
                "test_folder2",
                "test_string2.txt"
            )
        ]


class Test_HashOfString:
    """Test that the function hash_of_str works."""
    def test_hash_of_string(self):
        """Check for the hash of the test string."""
        assert misc_functions.hash_of_str(test_string) == \
            "b0a4de293503af7f9127cce50fbb3f8117e5c2ec8a0ec3cd4897e3995bacf0fd"

    def test_invalid_typed_input(self):
        """Check that the @strict notation works as expected."""
        with raises(TypeError):
            misc_functions.hash_of_str(593)
        with raises(TypeError):
            misc_functions.hash_of_str(['invalid', {'inputs': 5}])


class Test_HashOfFile():
    """Test that the function hash_of_file works."""
    def test_hash_of_file(self):
        """Check for the hash of the test_string.txt file."""
        assert misc_functions.hash_of_file(
            thisdir, "test_document_folder", "test_string.txt"
        ) == "b0a4de293503af7f9127cce50fbb3f8117e5c2ec8a0ec3cd4897e3995bacf0fd"

    def test_invalid_typed_input(self):
        """Check that the @strict notation works as expected."""
        with raises(TypeError):
            misc_functions.hash_of_str(593)
        with raises(TypeError):
            misc_functions.hash_of_str(['invalid', {'inputs': 5}], 987.6)


class TestPerms():
    """Test that the perms function returns the right values."""
    def test_regular_file(self):
        """Test the permissions of the plain text file."""
        with raises(ValueError):
            assert misc_functions.perms("test_string.txt")
        assert misc_functions.perms(
            thisdir, "test_document_folder", "test_string.txt"
        ) == 0o100644

    def test_executable_file(self):
        """Test the permissions of /bin/echo, an executable file."""
        assert misc_functions.perms(root, "bin", "echo") == 0o100755

    def test_folder(self):
        """Test the permissions of a folder that is accessible."""
        with raises(ValueError):
            misc_functions.perms("__pycache__")
        assert misc_functions.perms(
            thisdir, "__pycache__"
        ) == 0o40755

    def test_invalid_typed_input(self):
        """Check that the @strict notation works as expected."""
        with raises(TypeError):
            misc_functions.hash_of_str(593)
        with raises(TypeError):
            misc_functions.hash_of_str(['invalid', {'inputs': 5}], 987.6)


class Test_ReadRelative:
    """Tests for the read_relative function."""
    def test_readfile(self):
        """Get the contents of the test_string.txt file and verify it."""
        assert misc_functions.read_relative(
            "test_folder", "test_string.txt"
        ) == test_string

    def test_invalid_path(self):
        """Test that giving a read...() function raises OSError."""
        with raises(FileNotFoundError):
            misc_functions.read_("bullshit", "path")
        with raises(IsADirectoryError):
            misc_functions.read_("test_document_folder")

    def test_invalid_typed_input(self):
        """Make sure that passing invalidly typed arguments raises an error."""
        with raises(TypeError):
            misc_functions.read_relative(75, ["invalid", "input"])


class Test_ReadAbsolute:
    """Tests for the read_absolute function."""
    def test_readfile(self):
        """Get the contents of the test_string.txt file and verify it."""
        assert misc_functions.read_relative(
            thisdir, "test_folder", "test_string.txt"
        ) == test_string

    def test_invalid_path(self):
        """Test that giving a read...() function raises OSError."""
        with raises(FileNotFoundError):
            misc_functions.read_absolute("bullshit", "path")
        with raises(IsADirectoryError):
            misc_functions.read_absolute(thisdir, "test_document_folder")

    def test_invalid_typed_input(self):
        """Make sure that passing invalidly typed arguments raises an error."""
        with raises(TypeError):
            misc_functions.read_absolute(575.327, {"invalid": "input"})

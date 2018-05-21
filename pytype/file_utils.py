"""File and path utilities."""

import contextlib
import errno
import os
import shutil
import tempfile
import textwrap


def replace_extension(filename, new_extension):
  name, _ = os.path.splitext(filename)
  if new_extension.startswith("."):
    return name + new_extension
  else:
    return name + "." + new_extension


# TODO(mdemello): Should this go into pytd_utils instead, since no one else
# wants a versioned path?
def get_versioned_path(subdir, python_version):
  major_version = python_version[0]
  assert(major_version == 2 or major_version == 3)
  return os.path.join(subdir, str(major_version))


def makedirs(path):
  """Create a nested directory, but don't fail if any of it already exists."""
  try:
    os.makedirs(path)
  except OSError as e:
    if e.errno != errno.EEXIST:
      raise


class Tempdir(object):
  """Context handler for creating temporary directories."""

  def __enter__(self):
    self.path = tempfile.mkdtemp()
    return self

  def create_directory(self, filename):
    """Create a subdirectory in the temporary directory."""
    path = os.path.join(self.path, filename)
    makedirs(path)
    return path

  def create_file(self, filename, indented_data=None):
    """Create a file in the temporary directory. Dedents the data if needed."""
    filedir, filename = os.path.split(filename)
    if filedir:
      self.create_directory(filedir)
    path = os.path.join(self.path, filedir, filename)
    if isinstance(indented_data, bytes) and not isinstance(indented_data, str):
      # This is binary data rather than text.
      # TODO(rechen): The second isinstance() check can be dropped once we no
      # longer support running under Python 2.
      mode = "wb"
      data = indented_data
    else:
      mode = "w"
      data = textwrap.dedent(indented_data) if indented_data else indented_data
    with open(path, mode) as fi:
      if data:
        fi.write(data)
    return path

  def delete_file(self, filename):
    os.unlink(os.path.join(self.path, filename))

  def __exit__(self, error_type, value, tb):
    shutil.rmtree(path=self.path)
    return False  # reraise any exceptions

  def __getitem__(self, filename):
    """Get the full path for an entry in this directory."""
    return os.path.join(self.path, filename)


@contextlib.contextmanager
def cd(path):
  """Context manager. Change the directory, and restore it afterwards.

  Example usage:
    with cd("/path"):
      ...

  Arguments:
    path: The directory to change to.
  Yields:
    Executes your code, in a changed directory.
  """
  curdir = os.getcwd()
  os.chdir(path)
  try:
    yield
  finally:
    os.chdir(curdir)


def is_pyi_directory_init(filename):
  """Checks if a pyi file is path/to/dir/__init__.pyi."""
  if filename is None:
    return False
  return os.path.splitext(os.path.basename(filename))[0] == "__init__"


class NoSuchDirectory(Exception):
  pass


def load_pytype_file(filename):
  """Get the contents of a data file from the pytype installation.

  Arguments:
    filename: the path, relative to "pytype/"
  Returns:
    The contents of the file as a bytestring
  Raises:
    IOError: if file not found
  """
  path = os.path.join(os.path.dirname(__file__), filename)
  return load_data_file(path)


def load_data_file(path):
  """Get the contents of a data file."""
  with open(path, "rb") as fi:
    return fi.read()


def list_pytype_files(suffix):
  """Recursively get the contents of a directory in the pytype installation.

  This reports files in said directory as well as all subdirectories of it.

  Arguments:
    suffix: the path, relative to "pytype/"
  Yields:
    The filenames, relative to pytype/{suffix}
  Raises:
    NoSuchDirectory: if the directory doesn't exist.
  """
  basedir = os.path.join(os.path.dirname(__file__), suffix)
  assert not suffix.endswith("/")
  loader = globals().get("__loader__", None)
  try:
    # List directory using __loader__.
    # __loader__ exists only when this file is in a Python archive in Python 2
    # but is always present in Python 3, so we can't use the presence or
    # absence of the loader to determine whether calling get_zipfile is okay.
    filenames = loader.get_zipfile().namelist()  # pytype: disable=attribute-error
  except AttributeError:
    # List directory using the file system
    if not os.path.isdir(basedir):
      raise NoSuchDirectory(basedir)
    directories = [""]
    while directories:
      d = directories.pop()
      for basename in os.listdir(os.path.join(basedir, d)):
        filename = os.path.join(d, basename)
        if os.path.isdir(os.path.join(basedir, filename)):
          directories.append(filename)
        elif os.path.exists(os.path.join(basedir, filename)):
          yield filename
  else:
    for filename in filenames:
      directory = "pytype/" + suffix + "/"
      try:
        i = filename.rindex(directory)
      except ValueError:
        pass
      else:
        yield filename[i + len(directory):]



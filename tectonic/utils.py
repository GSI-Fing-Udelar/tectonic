
# Tectonic - An academic Cyber Range
# Copyright (C) 2024 Grupo de Seguridad Informática, Universidad de la República,
# Uruguay
#
# This file is part of Tectonic.
#
# Tectonic is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Tectonic is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Tectonic.  If not, see <http://www.gnu.org/licenses/>.

from prettytable import PrettyTable, TableStyle
import os
from os.path import isfile, join, isdir
from pathlib import Path


def create_table(headers, rows):
    table = PrettyTable()
    table.set_style(TableStyle.SINGLE_BORDER)
    table.field_names = headers
    table.add_rows(rows)
    return f"\n{table}"

def list_files_in_directory(directory_path):
    """
    Returns full path to files in directory

    Parameters:
        directory_path: path to directory
    
    Returns:
        list: full path to files in directory
    """
    if isdir(directory_path):
        return [join(directory_path, f) for f in os.listdir(directory_path) if isfile(join(directory_path, f))]
    else:
        return []


def absolute_path(path, base_dir=None, expand_user=True):
    """Return an absolute path if the given path is relative.
    
    Expand starting tilde to the user homedir if expand_user is True.
    Returns path unchanged if there is an error.
    """
    if base_dir is None:
        base_dir = os.getcwd()
    try:
        p = Path(path)
        if expand_user:
            p = p.expanduser()
        if not p.is_absolute():
            p = Path(base_dir).joinpath(p)
    except:
        return path
    return str(p)

def read_files_in_dir(directory):
    contents = ""
    if directory and Path(directory).is_dir():
        for child in Path(directory).iterdir():
            if child.is_file():
                content = child.read_text()
                if not content or content[-1] != "\n":
                    content += "\n"
                contents += content
    return contents

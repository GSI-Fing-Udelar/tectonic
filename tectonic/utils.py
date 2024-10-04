
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

from prettytable import PrettyTable, SINGLE_BORDER
from os import listdir
from os.path import isfile, join, isdir

def create_table(headers, rows):
    table = PrettyTable()
    table.set_style(SINGLE_BORDER)
    table.field_names = headers
    table.add_rows(rows)
    return table

def read_files_in_directory(directory_path):
    """
    Returns full path to files in directory

    Parameters:
        directory_path: path to directory
    
    Returns:
        list: full path to files in directory
    """
    if isdir(directory_path):
        return [join(directory_path, f) for f in listdir(directory_path) if isfile(join(directory_path, f))]
    else:
        return []
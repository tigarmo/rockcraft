# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2020-2021 Canonical Ltd.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License version 3 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""The python plugin."""


from typing import Any, Dict, List, Set, cast, Optional, Tuple

from overrides import override

from ._parts_python_plugin import PythonPlugin as PartsPythonPlugin


SHEBANG = r"""#\!/bin/python3.10"""


class RockcraftPythonPlugin(PartsPythonPlugin):
    @override
    def get_base_python(self) -> Tuple[Optional[str], str]:
        return (None, "ROCKs must always use part-provided python")

    @override
    def get_shebang_target(self) -> str:
        return SHEBANG

    @override
    def should_remove_symlinks(self) -> bool:
        return self._part_info.base != "bare"

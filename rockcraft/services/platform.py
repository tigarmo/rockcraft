from __future__ import annotations

import abc
from typing import TYPE_CHECKING

from craft_application.services import base
from overrides import override

from rockcraft.models.project import load_project

if TYPE_CHECKING:  # pragma: no cover
    import pathlib

    from craft_application import models


class PlatformService(base.BaseService):
    """Business logic for creating packages."""

    @abc.abstractmethod
    def build_plan(self) -> list[tuple[str, str]]:
        pass


class RockcraftPlatformService(PlatformService):
    def build_plan(self) -> list[tuple[str, str]]:
        build_infos = []
        for platform_entry, platform in self._project.platforms.items():
            build_for = (
                platform["build_for"][0]
                if platform.get("build_for")
                else platform_entry
            )
            build_for_variant = platform.get("build_for_variant")
            build_on = build_for
            build_infos.append((build_on, build_for))
        return build_infos

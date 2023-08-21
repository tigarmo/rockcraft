# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2022 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Rockcraft lifecycle commands."""

from __future__ import annotations

import abc
import argparse
import textwrap
from typing import TYPE_CHECKING, Any

from craft_application.commands import AppCommand
from craft_application.commands import lifecycle as base_lifecycle
from craft_cli import BaseCommand, emit
from overrides import overrides, override


if TYPE_CHECKING:
    from rockcraft.application import Rockcraft


class _LifecycleCommand(AppCommand, abc.ABC):
    """Lifecycle-related commands."""

    # @overrides
    # def run(self, parsed_args: "argparse.Namespace") -> None:
    #     """Run the command."""
    #     if not self.name:
    #         raise RuntimeError("command name not specified")
    #
    #     emit.trace(f"lifecycle command: {self.name!r}, arguments: {parsed_args!r}")
    # TODO
    # lifecycle.run(self.name, parsed_args)

    def fill_parser(self, parser: argparse.ArgumentParser) -> None:
        super().fill_parser(parser)  # type: ignore
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Shell into the environment if the build fails",
        )
        parser.add_argument(
            "--destructive-mode",
            action="store_true",
            help="Build in the current host",
        )


class _LifecycleStepCommand(_LifecycleCommand):
    """Lifecycle step commands."""

    @overrides
    def fill_parser(self, parser: argparse.ArgumentParser) -> None:
        super().fill_parser(parser)  # type: ignore
        parser.add_argument(
            "parts",
            metavar="part-name",
            type=str,
            nargs="*",
            help="Optional list of parts to process",
        )

        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--shell",
            action="store_true",
            help="Shell into the environment in lieu of the step to run.",
        )
        group.add_argument(
            "--shell-after",
            action="store_true",
            help="Shell into the environment after the step has run.",
        )

    @override
    def run(
        self, parsed_args: argparse.Namespace, step_name: str | None = None
    ) -> None:
        """Run a lifecycle step command."""
        super().run(parsed_args)

        step_name = step_name or self.name

        self._services.lifecycle.run(step_name=step_name, part_names=parsed_args.parts)


class CleanCommand(_LifecycleStepCommand):
    """Command to remove part assets."""

    name = "clean"
    help_msg = "Remove a part's assets"
    overview = textwrap.dedent(
        """
        Clean up artifacts belonging to parts. If no parts are specified,
        remove the ROCK packing environment.
        """
    )


class PullCommand(_LifecycleStepCommand):
    """Command to pull parts."""

    name = "pull"
    help_msg = "Download or retrieve artifacts defined for a part"
    overview = textwrap.dedent(
        """
        Download or retrieve artifacts defined for a part. If part names
        are specified only those parts will be pulled, otherwise all parts
        will be pulled.
        """
    )


class OverlayCommand(_LifecycleStepCommand):
    """Command to overlay parts."""

    name = "overlay"
    help_msg = "Create part layers over the base filesystem."
    overview = textwrap.dedent(
        """
        Execute operations defined for each part on a layer over the base
        filesystem, potentially modifying its contents.
        """
    )


class BuildCommand(_LifecycleStepCommand):
    """Command to build parts."""

    name = "build"
    help_msg = "Build artifacts defined for a part"
    overview = textwrap.dedent(
        """
        Build artifacts defined for a part. If part names are specified only
        those parts will be built, otherwise all parts will be built.
        """
    )


class StageCommand(_LifecycleStepCommand):
    """Command to stage parts."""

    name = "stage"
    help_msg = "Stage built artifacts into a common staging area"
    overview = textwrap.dedent(
        """
        Stage built artifacts into a common staging area. If part names are
        specified only those parts will be staged. The default is to stage
        all parts.
        """
    )


class PrimeCommand(_LifecycleStepCommand):
    """Command to prime parts."""

    name = "prime"
    help_msg = "Prime artifacts defined for a part"
    overview = textwrap.dedent(
        """
        Prepare the final payload to be packed as a ROCK, performing additional
        processing and adding metadata files. If part names are specified only
        those parts will be primed. The default is to prime all parts.
        """
    )


class PackCommand(base_lifecycle.PackCommand):
    """Command to pack the final artifact."""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        self._application: Rockcraft = config["application"]

    name = "pack"
    help_msg = "Create the ROCK"
    overview = textwrap.dedent(
        """
        Process parts and create the ROCK as an OCI archive file containing
        the project payload with the provided metadata.
        """
    )

    @override
    def run(
        self, parsed_args: argparse.Namespace, step_name: str | None = None
    ) -> None:
        """Run the pack command."""
        if step_name not in ("pack", None):
            raise RuntimeError(f"Step name {step_name} passed to pack command.")

        self._application.run_command("pack", parsed_args)

    def fill_parser(self, parser: argparse.ArgumentParser) -> None:
        super().fill_parser(parser)  # type: ignore
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Shell into the environment if the build fails",
        )
        parser.add_argument(
            "--destructive-mode",
            action="store_true",
            help="Build in the current host",
        )

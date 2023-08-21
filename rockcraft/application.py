from __future__ import annotations

import argparse
import os
import pathlib
import signal
import subprocess
import sys
from typing import cast

import craft_cli
import craft_providers
from craft_application import AppMetadata, Application, commands
from craft_cli import emit
from overrides import override

from rockcraft import cli, plugins
from rockcraft.models import project

APP_METADATA = AppMetadata(
    name="rockcraft",
    summary="A tool to create OCI images",
    ProjectClass=project.Project,
)


class Rockcraft(Application):
    """Rockcraft application definition."""

    def _configure_services(self) -> None:
        super()._configure_services()
        self.services.set_kwargs(
            "package",
            work_dir=self._work_dir,
            prime_dir=self._work_dir / "prime",
        )

    @property
    @override
    def command_groups(self) -> list[craft_cli.CommandGroup]:
        """Return command groups."""
        return cli.COMMAND_GROUPS

    @override
    def run(self) -> int:
        """Bootstrap and run the application."""
        plugins.register()
        dispatcher = self._get_dispatcher()
        self._configure_services()
        craft_cli.emit.trace("Preparing application...")

        return_code = 1  # General error
        try:
            command = cast(
                commands.AppCommand,
                dispatcher.load_command(
                    {
                        "app": self.app,
                        "services": self.services,
                        "application": self,
                    }
                ),
            )
            return_code = dispatcher.run() or 0
        except KeyboardInterrupt as err:
            self._emit_error(craft_cli.CraftError("Interrupted."), cause=err)
            return_code = 128 + signal.SIGINT
        except craft_cli.CraftError as err:
            self._emit_error(err)
        except Exception as err:  # noqa: BLE001 pylint: disable=broad-except
            self._emit_error(
                craft_cli.CraftError(f"{self.app.name} internal error: {err!r}")
            )
            if os.getenv("CRAFT_DEBUG") == "1":
                raise
            return_code = 70  # EX_SOFTWARE from sysexits.h
        else:
            craft_cli.emit.ended_ok()

        return return_code

    def run_command(self, command_name: str, parsed_args: argparse.Namespace) -> None:
        emit.trace(f"command: {command_name}, arguments: {parsed_args}")

        # TODO: need a "specialization hook" for things like SNAPCRAFT_BUILD_MODE
        managed_mode = self.services.ProviderClass.is_managed()
        destructive_mode = getattr(parsed_args, "destructive_mode", False)
        provider_mode = not managed_mode and not destructive_mode

        step_name = "prime" if command_name == "pack" else command_name

        # TODO: load the raw yaml and pass it to build_plan?
        for build_info in self.services.platform.build_plan():
            # apply yaml
            # create the project
            if provider_mode:
                self.run_managed(command_name, build_info)
            else:
                lifecycle_data = self.services.lifecycle.run(
                    build_info, step_name, getattr(parsed_args, "parts", None)
                )
                if command_name == "pack":
                    self.services.package.pack(parsed_args.output, lifecycle_data)

    def run_managed(self, command, build_info) -> None:
        """Run the application in a managed instance."""
        if command == "clean":
            self.clean_provider(build_info)
            return

        craft_cli.emit.debug(f"Running {self.app.name} in a managed instance...")
        instance_path = pathlib.PosixPath("/root/project")
        with self.services.provider.instance(
            self.project.effective_base, work_dir=self._work_dir
        ) as instance:
            try:
                with emit.pause():
                    # Pyright doesn't fully understand craft_providers's CompletedProcess.
                    instance.execute_run(  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
                        [self.app.name, *sys.argv[1:]], cwd=instance_path, check=True
                    )
            except subprocess.CalledProcessError as exc:
                raise craft_providers.ProviderError(
                    f"Failed to execute {self.app.name} in instance."
                ) from exc

    def get_instance_name(self, build_info):
        work_dir_inode = self._work_dir.stat().st_ino
        instance_name = f"{self._app.name}-{self._project.name}-{work_dir_inode}"
        return instance_name

    def clean_provider(self, build_info):
        """Clean the provider environment.

        :param project_name: name of the project
        :param project_path: path of the project
        """
        emit.progress("Cleaning build provider")
        provider = self.services.provider.get_provider()
        instance_name = self.get_instance_name(build_info)
        emit.debug(f"Cleaning instance {instance_name}")
        provider.clean_project_environments(instance_name=instance_name)
        emit.progress("Cleaned build provider", permanent=True)

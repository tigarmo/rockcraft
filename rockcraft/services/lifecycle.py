from __future__ import annotations

from pathlib import Path

from craft_application import LifecycleService, errors
from craft_cli import emit
from craft_parts import LifecycleManager, PartsError
from overrides import override

from rockcraft import oci
from rockcraft.lifecycle import _expand_environment
from rockcraft.models.project import load_project, Project
from rockcraft.parts import PartsLifecycle


class RockcraftLifecycleService(LifecycleService):
    @override
    def _init_lifecycle_manager(self) -> LifecycleManager:
        """Create and return the Lifecycle manager.

        An application may override this method if needed if the lifecycle
        manager needs to be called differently.
        """
        emit.debug(f"Initialising lifecycle manager in {self._work_dir}")
        emit.trace(f"Lifecycle: {repr(self)}")
        try:
            return LifecycleManager(
                {"parts": {}},
                application_name=self._app.name,
                cache_dir=self._cache_dir,
                work_dir=self._work_dir,
                ignore_local_sources=self._app.source_ignore_patterns,
                **self._manager_kwargs,
            )
        except PartsError as err:
            raise errors.PartsLifecycleError.from_parts_error(err) from err

    def run(
        self, build_info, step_name: str, part_names: list[str] | None = None
    ) -> dict:

        image_dir = self._work_dir / "images"
        bundle_dir = self._work_dir / "bundles"

        project_yaml = load_project(Path("rockcraft.yaml"))

        project_vars = {"version": project_yaml["version"]}
        # Expand the environment so that the global variables can be interpolated
        _expand_environment(
            project_yaml,
            project_vars=project_vars,
            work_dir=self._work_dir,
        )
        project = Project.unmarshal(project_yaml)

        if project.package_repositories is None:
            package_repositories = []
        else:
            package_repositories = project.package_repositories

        emit.progress(f"Retrieving base {project.base}")

        build_on, build_for = build_info
        if project.base == "bare":
            base_image, source_image = oci.Image.new_oci_image(
                f"{project.base}:latest",
                image_dir=image_dir,
                arch=build_for,
                variant=None,  # TODO must come from build_info
            )
        else:
            base_image, source_image = oci.Image.from_docker_registry(
                project.base,
                image_dir=image_dir,
                arch=build_for,
                variant=None,  # TODO must come from build_info
            )
        emit.progress(f"Retrieved base {project.base} for {build_for}", permanent=True)

        emit.progress(f"Extracting {base_image.image_name}")
        rootfs = base_image.extract_to(bundle_dir)
        emit.progress(f"Extracted {base_image.image_name}", permanent=True)

        # TODO: check if destination image already exists, etc.
        project_base_image = base_image.copy_to(
            f"{project.name}:rockcraft-base", image_dir=image_dir
        )

        base_digest = project_base_image.digest(source_image)

        lifecycle = PartsLifecycle(
            project.parts,
            project_name=project.name,
            project_vars=project_vars,
            work_dir=self._work_dir,
            part_names=part_names,
            base_layer_dir=rootfs,
            base_layer_hash=base_digest,
            base=project.base,
            package_repositories=package_repositories,
        )

        if False:
            lifecycle.clean()
            return {}

        lifecycle.run(
            step_name,
            shell=False,  # getattr(parsed_args, "shell", False),
            shell_after=False,  # getattr(parsed_args, "shell_after", False),
            debug=False,  # getattr(parsed_args, "debug", False),
        )

        return {
            "project": project,
            "project_base_image": project_base_image,
            "base_digest": base_digest,
            "rock_suffix": build_for,
            "build_for": build_for,
            "base_layer_dir": rootfs,
        }

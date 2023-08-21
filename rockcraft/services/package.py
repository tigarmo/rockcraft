from __future__ import annotations

import datetime
import pathlib
from typing import cast

from craft_application import services, AppMetadata
from craft_cli import emit
from overrides import override

from rockcraft import oci
from rockcraft.models.project import Project
from rockcraft.usernames import SUPPORTED_GLOBAL_USERNAMES


class RockcraftPackageService(services.PackageService):
    """Package service subclass for Sourcecraft."""

    def __init__(
        self,
        app: AppMetadata,
        project: Project,
        *,
        work_dir: pathlib.Path,
        prime_dir: pathlib.Path,
    ) -> None:
        super().__init__(app, project)
        self._work_dir = work_dir
        self._prime_dir = prime_dir

    def pack(self, dest: pathlib.Path, lifecycle_data) -> list[pathlib.Path]:
        """Create one or more packages as appropriate.

        :param dest: Directory into which to write the package(s).
        :returns: A list of paths to created packages.
        """
        project = cast(Project, self._project)
        # source_part = project.source_part or project.name
        # source_part_directory = self._work_dir / "parts" / source_part / "src"
        # self.write_metadata(self._prime_dir)
        #
        # source_package_name = f"{self._project.name}_{self._project.version}.tar.xz"
        # with tarfile.open(dest / source_package_name, mode="w:xz") as tar:
        #     tar.add(source_part_directory, arcname=".", recursive=True)
        #     tar.add(self._prime_dir / "metadata.yaml", arcname="metadata.yaml")
        project = cast(Project, self._project)
        archive_name = _pack(
            prime_dir=self._prime_dir,
            project=lifecycle_data["project"],
            project_base_image=lifecycle_data["project_base_image"],
            base_digest=lifecycle_data["base_digest"],
            rock_suffix=lifecycle_data["rock_suffix"],
            build_for=lifecycle_data["build_for"],
            base_layer_dir=lifecycle_data["base_layer_dir"],
        )
        return [dest / archive_name]

    @override
    def write_metadata(self, path: pathlib.Path) -> None:
        # TODO
        pass

    @property
    def metadata(self) -> models.SourceMetadata:
        """Generate the source.yaml model for the output file."""
        project = cast(models.SourceProject, self._project)
        return models.SourceMetadata(
            name=project.name,
            version=project.version,
            base=project.base,
        )


def _pack(
    prime_dir: pathlib.Path,
    *,
    project: Project,
    project_base_image: oci.Image,
    base_digest: bytes,
    rock_suffix: str,
    build_for: str,
    base_layer_dir: pathlib.Path,
) -> str:
    """Create the rock image for a given architecture.

    :param lifecycle:
      The lifecycle object containing the primed payload for the rock.
    :param project_base_image:
      The Image for the base over which the payload was primed.
    :param base_digest:
      The digest of the base image, to add to the new image's metadata.
    :param rock_suffix:
      The suffix to append to the image's filename, after the name and version.
    :param build_for:
      The architecture of the built rock, to add as metadata.
    :param base_layer_dir:
      The directory where the rock's base image was extracted.
    """
    emit.progress("Creating new layer")
    new_image = project_base_image.add_layer(
        tag=project.version,
        new_layer_dir=prime_dir,
        base_layer_dir=base_layer_dir,
    )
    emit.progress("Created new layer", permanent=True)

    if project.run_user:
        emit.progress(f"Creating new user {project.run_user}")
        new_image.add_user(
            prime_dir=prime_dir,
            base_layer_dir=base_layer_dir,
            tag=project.version,
            username=project.run_user,
            uid=SUPPORTED_GLOBAL_USERNAMES[project.run_user]["uid"],
        )

        emit.progress(f"Setting the default OCI user to be {project.run_user}")
        new_image.set_default_user(project.run_user)

    emit.progress("Adding Pebble entrypoint")

    new_image.set_entrypoint()

    services = project.dict(exclude_none=True, by_alias=True).get("services", {})

    checks = project.dict(exclude_none=True, by_alias=True).get("checks", {})

    if services or checks:
        new_image.set_pebble_layer(
            services=services,
            checks=checks,
            name=project.name,
            tag=project.version,
            summary=project.summary,
            description=project.description,
            base_layer_dir=base_layer_dir,
        )

    if project.environment:
        new_image.set_environment(project.environment)

    # Set annotations and metadata, both dynamic and the ones based on user-provided properties
    # Also include the "created" timestamp, just before packing the image
    emit.progress("Adding metadata")
    oci_annotations, rock_metadata = project.generate_metadata(
        datetime.datetime.now(datetime.timezone.utc).isoformat(), base_digest
    )
    rock_metadata["architecture"] = build_for
    # TODO: add variant to rock_metadata too
    # if build_for_variant:
    #     rock_metadata["variant"] = build_for_variant
    new_image.set_annotations(oci_annotations)
    new_image.set_control_data(rock_metadata)
    emit.progress("Metadata added")

    emit.progress("Exporting to OCI archive")
    archive_name = f"{project.name}_{project.version}_{rock_suffix}.rock"
    new_image.to_oci_archive(tag=project.version, filename=archive_name)
    emit.progress(f"Exported to OCI archive '{archive_name}'", permanent=True)

    return archive_name

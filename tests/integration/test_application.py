from __future__ import annotations

from dataclasses import dataclass
from textwrap import dedent

import craft_application
from craft_application import ServiceFactory

from rockcraft import application
from rockcraft.services.lifecycle import RockcraftLifecycleService
from rockcraft.services.package import RockcraftPackageService
from rockcraft.services.platform import PlatformService, RockcraftPlatformService
from rockcraft.services.provider import RockcraftProviderService

app_metadata = application.APP_METADATA


@dataclass
class RockcraftServiceFactory(ServiceFactory):

    PlatformClass: type[PlatformService] = RockcraftPlatformService


def test_pack_clean(monkeypatch, tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    # monkeypatch.setenv("ROCKCRAFT_MANAGED_MODE", "1")
    monkeypatch.setenv("CRAFT_DEBUG", "1")
    monkeypatch.setattr("sys.argv", ["rockcraft", "pack", "--destructive-mode"])
    # monkeypatch.setattr("sys.argv", ["rockcraft", "pack"])

    project_path = project_dir / "rockcraft.yaml"
    project_path.write_text(
        dedent(
            """\
            name: bare-base-test
            version: latest
            summary: A tiny ROCK
            description: Building a tiny ROCK from a bare base, with just one package
            license: Apache-2.0
            build-base: ubuntu:22.04
            base: bare
            services:
              hello:
                override: merge
                command: /usr/bin/hello -g "ship it!"
                startup: enabled
            platforms:
              amd64:
            
            parts:
              hello:
                plugin: nil
        """
        )
    )

    monkeypatch.chdir(project_dir)
    services = RockcraftServiceFactory(
        app=app_metadata,
        PackageClass=RockcraftPackageService,
        ProviderClass=RockcraftProviderService,
        PlatformClass=RockcraftPlatformService,
        LifecycleClass=RockcraftLifecycleService,
    )

    app = application.Rockcraft(app_metadata, services)

    result = app.run()

    assert result == 0
    assert (project_dir / "prime").exists()
    assert (project_dir / "bare-base-test_latest_amd64.rock").exists()
    return
    check.is_true((project_dir / "parts").exists())
    check.is_true((project_dir / "stage").exists())
    metadata_file = project_dir / "prime/metadata.yaml"
    check.is_true(metadata_file.exists())
    metadata = models.SourceMetadata.from_yaml_file(metadata_file)
    check.equal(metadata.name, app.project.name)
    check.equal(metadata.version, app.project.version)
    source_file = project_dir / f"{metadata.name}_{metadata.version}.tar.xz"
    check.is_true(source_file.exists())
    with tarfile.open(source_file) as tar:
        tar_metadata = models.SourceMetadata.unmarshal(
            yaml.safe_load(
                tar.extractfile(
                    "metadata.yaml"
                )  # pyright: ignore[reportGeneralTypeIssues]
            )
        )
    check.equal(tar_metadata, metadata)

    monkeypatch.setattr("sys.argv", ["sourcecraft", "clean"])
    result = app.run()

    assert result == 0
    check.is_false((project_dir / "prime").exists())
    check.is_false((project_dir / "parts").exists())
    check.is_false((project_dir / "stage").exists())

# Rockcraft AI Agent Instructions

This document provides guidance for AI agents working on the Rockcraft codebase.

## 1. Project Overview & Architecture

Rockcraft is a command-line tool for building OCI-compliant container images called "rocks". It is built upon the `craft-*` family of libraries (e.g., `craft-application`, `craft-parts`), which provide the core application framework, lifecycle management, and plugin system.

- **Core Configuration**: The central piece of user configuration is the `rockcraft.yaml` file. Its structure is defined by the Pydantic model in `rockcraft/models/project.py`. Most feature work will involve changes to this model.
- **Application Entrypoint**: The main application is defined in `rockcraft/application.py` (`Rockcraft` class) and the command-line interface is managed in `rockcraft/cli.py`.
- **Service-Oriented Architecture**: The business logic is organized into services located in the `rockcraft/services/` directory. These services are managed by the `RockcraftServiceFactory` (`rockcraft/services/service_factory.py`) and handle distinct concerns like project parsing, image building, and lifecycle management. When adding new logic, consider which service it belongs to.
- **Plugin System**: Rockcraft is extensible via plugins, which are located in `rockcraft/plugins/`. See `rockcraft/plugins/register.py` for how they are discovered and registered.
- **Pebble Integration**: Rocks use Pebble for process management inside the container. The `add_pebble_part` function in `rockcraft/pebble.py` automatically injects the Pebble part into the build. Services are defined in `rockcraft.yaml` under the `services:` key.

## 2. Developer Workflow

The primary development workflow is managed through `make`. See `Makefile` and `common.mk` for all available targets.

- **Setup**: To set up the development environment, install dependencies, and configure pre-commit hooks, run:
    ```bash
    make setup
    ```
- **Linting & Formatting**: The project uses `ruff` for linting and formatting, and `pyright`/`mypy` for type checking.
    - To format all files: `make format`
    - To run all linters: `make lint`
- **Testing**: Tests are written with `pytest` and are located in the `tests/` directory.
    - To run all tests: `make test`
    - To run only fast tests: `make test-fast`
    - To generate a coverage report: `make test-coverage`
- **Building the Snap**: To build the Rockcraft snap package for testing:
    ```bash
    snapcraft pack
    ```

## 3. Code Conventions

- **Commit Messages**: Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification. See `HACKING.md` for detailed guidelines on types, scopes, and formatting.
- **Pydantic Models**: The core data structures are defined using Pydantic in `rockcraft/models/`. When adding or modifying configuration options in `rockcraft.yaml`, you must update the `Project` model in `rockcraft/models/project.py`.
- **Testing**:
    - Unit tests are in `tests/unit/`.
    - Integration tests are in `tests/integration/`.
    - Use fixtures defined in `tests/conftest.py` to mock services and set up project files. The `fake_services` fixture is essential for testing service interactions.
    - To test a feature that requires a specific `rockcraft.yaml` configuration, use the `fake_project_file` fixture in conjunction with `pytest.mark.parametrize` and the `project_keys` fixture.
    - Tests that take longer than 1 second to run should be marked with the `@pytest.mark.slow` decorator. This allows them to be skipped during a fast test run (`make test-fast`).
- **Dependencies**: Project dependencies are managed in `pyproject.toml` using `uv`.

## 4. Key Files & Directories

- `rockcraft.yaml`: The main project definition file for creating a rock.
- `rockcraft/`: The main source code for the application.
- `rockcraft/models/project.py`: Defines the schema for `rockcraft.yaml`. **This is a critical file.**
- `rockcraft/services/`: Contains the core business logic, organized by service.
- `rockcraft/cli.py`: The command-line entry point and command definitions.
- `tests/`: Contains all unit and integration tests.
- `tests/conftest.py`: Defines shared pytest fixtures.
- `Makefile` & `common.mk`: Define the main development tasks.
- `HACKING.md`: Detailed contribution guide, including commit message and branching strategy.

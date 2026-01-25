# coreason-maco

**Multi-Agent Collaborative Orchestrator**

[![CI/CD](https://github.com/CoReason-AI/coreason_maco/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/CoReason-AI/coreason_maco/actions/workflows/ci-cd.yml)
[![PyPI](https://img.shields.io/pypi/v/coreason_maco.svg)](https://pypi.org/project/coreason_maco/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/coreason_maco.svg)](https://pypi.org/project/coreason_maco/)
[![License](https://img.shields.io/github/license/CoReason-AI/coreason_maco)](https://github.com/CoReason-AI/coreason_maco/blob/main/LICENSE)
[![Codecov](https://codecov.io/gh/CoReason-AI/coreason_maco/branch/main/graph/badge.svg)](https://codecov.io/gh/CoReason-AI/coreason_maco)
[![Downloads](https://static.pepy.tech/badge/coreason_maco)](https://pepy.tech/project/coreason_maco)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

## Overview

`coreason-maco` is a specialized Python library designed to **facilitate the orchestration of autonomous agents**. It provides a robust foundation for **deterministic, GxP-compliant workflows** and **real-time "Glass Box" telemetry**, enabling developers to build scalable and verifiable systems.

## Key Features

* **Feature A:** **Deterministic Orchestration:** Executes complex recipes with predictable, verifiable outcomes.
* **Feature B:** **Live Telemetry:** Streams granular `GraphEvent`s for real-time visualization of the reasoning process.
* **Integration:** Seamlessly integrates with the Coreason ecosystem.

## Getting Started

### Prerequisites
- Python 3.12+
- Poetry

### Installation

```sh
pip install coreason_maco
```

1.  Clone the repository:
    ```sh
    git clone https://github.com/CoReason-AI/coreason_maco.git
    cd coreason_maco
    ```
2.  Install dependencies:
    ```sh
    poetry install
    ```

### Usage

-   Run the linter:
    ```sh
    poetry run pre-commit run --all-files
    ```
-   Run the tests:
    ```sh
    poetry run pytest
    ```

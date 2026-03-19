# Contributing to Golf Modeling Suite

Thank you for your interest in contributing! This document provides guidelines for contributing to the Golf Modeling Suite.

## 🚀 Quick Start

1. **Fork** the repository
2. **Clone** your fork locally
3. **Create a branch**: `git checkout -b feature/your-feature-name`
4. **Make changes** following our coding standards
5. **Test** your changes: `pytest`
6. **Commit** with a descriptive message
7. **Push** and create a Pull Request

## 📋 Development Setup

```bash
# Clone the repository
git clone https://github.com/D-sorganization/UpstreamDrift.git
cd UpstreamDrift

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install the supported default surface
pip install -e ".[dev]"

# Optional: add Drake + Pinocchio for cross-engine work
pip install -e ".[dev,all-engines]"
```

See `docs/engines/support_tiers.md` before enabling heavier or experimental
engine combinations.

## ✅ Code Standards

### Python

- **Formatter**: Black (default settings)
- **Linter**: Ruff
- **Type Checker**: MyPy (see note below)
- Use type hints for all new functions
- Use `logging` instead of `print()`
- Follow existing patterns in the codebase

> **Note on Type Checking**: While MyPy is part of our quality toolchain, strict type checking
> is not yet fully enforced across the legacy codebase. New code should include type hints.

### Before Committing

Use the Makefile for convenience:

```bash
make format   # Format with black and ruff
make lint     # Run ruff and mypy
make test     # Run pytest
make check    # Run all checks
```

Or run commands directly:

```bash
python3 -m black .
python3 -m ruff check . --fix
python3 -m mypy .
python3 -m pytest
```

> **Note on Tests**: Because our CI pipeline strictly checks test files, please run `ruff check tests/ --fix` and `black tests/` before submitting to prevent failures on test suites.

## 🎯 Physics Engine Guidelines

Current support tiers:

- **Supported default**: MuJoCo
- **Extended cross-engine**: Drake, Pinocchio
- **Experimental / stub**: OpenSim, MyoSuite

See `docs/engines/support_tiers.md` and
`docs/engines/engine_capabilities.md` before widening an engine-facing change.

When adding engine-specific code:

- Follow the existing adapter pattern
- Implement the PhysicsEngine protocol
- Add corresponding tests

## 🧪 Testing

- 1,563+ tests in the test suite
- Add tests for new functionality
- Run `pytest` before submitting PR
- Use existing test fixtures where possible

### Test Markers

The project uses pytest markers to categorize tests by their runtime requirements:

| Marker | Description | When to use |
|--------|-------------|-------------|
| `live_simulation` | Tests that require a running physics simulation engine (MuJoCo, Drake, Pinocchio, etc.) | Any test that invokes a real physics engine, runs a simulation loop, or requires hardware-in-the-loop |
| `slow` | Slow-running tests | Tests that take more than a few seconds |
| `integration` | Integration tests | Tests that exercise multiple components together |
| `requires_gl` | Tests needing OpenGL/display | Tests that require a graphics context |
| `requires_network` | Tests needing network | Tests that make network calls |

**`live_simulation` marker usage:**

```python
import pytest

@pytest.mark.live_simulation
def test_mujoco_physics_step():
    """This test requires MuJoCo to be installed and functional."""
    import mujoco
    # ... test body
```

**Running and filtering:**

```bash
# Run only live_simulation tests (requires physics engines installed)
pytest -m live_simulation

# Exclude live_simulation tests (standard CI mode)
pytest -m "not live_simulation"

# Collect live_simulation tests without running them
pytest --co -m live_simulation
```

**CI integration:**
- Standard CI (`ci-standard.yml`) excludes `live_simulation` tests — they require native engine installations not available in the base CI environment.
- Nightly cross-engine workflow (`nightly-cross-engine.yml`) explicitly includes and runs `live_simulation` tests on the fleet runner with full engine dependencies.

## 📝 Commit Messages

Follow conventional commits:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `test:` Testing changes

Example: `feat(mujoco): Add contact force visualization`

## 📖 Documentation

- Update CHANGELOG.md under [Unreleased]
- Add docstrings with parameter descriptions
- Update engine-specific docs if applicable

## 🤝 Pull Request Process

1. Ensure CI passes (ruff, black, mypy, pytest)
2. Update documentation
3. Request review from maintainers

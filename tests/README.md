# Tests

This directory contains tests for the Diary application.

## Backend Tests (Python)

Backend tests use `pytest` and are located in the `tests/` directory.

### Running Tests

```bash
# Install dependencies (if not already installed)
pip install -r server/requirements.txt

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_photos_repo.py

# Run specific test
pytest tests/test_photos_repo.py::TestSafeName::test_normal_name

# Run with coverage
pytest --cov=server --cov-report=html
```

### Test Structure

- `conftest.py` - Shared fixtures and configuration
- `test_photos_repo.py` - Tests for photo repository functions
- `test_exif_utils.py` - Tests for EXIF utilities
- `test_api.py` - Tests for FastAPI endpoints

### Writing Tests

Tests follow pytest conventions:
- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

Use fixtures from `conftest.py`:
- `temp_data_dir` - Temporary data directory for file operations
- `sample_image` - Sample image file for testing
- `sample_sidecar_data` - Sample sidecar JSON data

## Frontend Tests (TypeScript/React)

Frontend tests use `Vitest` and React Testing Library.

### Running Tests

```bash
cd diary-app

# Install dependencies (if not already installed)
npm install

# Run tests in watch mode
npm test

# Run tests once
npm test -- --run

# Run tests with UI
npm run test:ui

# Run tests with coverage
npm run test:coverage
```

### Test Structure

Tests are co-located with source files:
- `src/lib/__tests__/` - Utility function tests
- Component tests should be placed next to components

### Writing Tests

Example test:
```typescript
import { describe, it, expect } from 'vitest'
import { myFunction } from '../myFunction'

describe('myFunction', () => {
  it('does something', () => {
    expect(myFunction()).toBe(expected)
  })
})
```

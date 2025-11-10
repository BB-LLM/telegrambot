# Test Suite

This directory contains all test files for the Soul MVP project.

## Test Files

- `test_database.py` - Database functionality tests
- `test_complete_core.py` - Complete core functionality tests  
- `test_ai_integration.py` - AI model integration tests

## Running Tests

From the project root directory:

```bash
# Run all tests
python -m pytest app/test/

# Run specific test file
python -m pytest app/test/test_database.py

# Run with verbose output
python -m pytest app/test/ -v
```

## Path Configuration

All test files have been configured to correctly import from the `app` module by:
1. Getting the project root directory (3 levels up from `app/test/`)
2. Adding it to `sys.path` using `sys.path.insert(0, project_root)`
3. Using absolute imports from `app.*`

This ensures tests can run from any location and properly import the application modules.


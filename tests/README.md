# DocuMind AI Test Suite

This directory contains the test suite for DocuMind AI, covering all phases of the document processing pipeline.

## Test Structure

```
tests/
├── __init__.py          # Package initialization
├── conftest.py          # Pytest configuration and fixtures
├── test_basic.py        # Basic functionality tests (no heavy deps)
├── test_processing.py   # Phase 3 processing component tests
├── test_retrieval.py    # Phase 4 retrieval component tests
├── test_integration.py  # End-to-end integration tests
├── run_tests.py         # Test runner script
└── README.md           # This file
```

## Running Tests

### Quick Start (Basic Tests)
```bash
cd tests
python test_basic.py
```

### Using the Test Runner
```bash
cd tests
python run_tests.py
```

### Using Pytest (Full Suite)
```bash
# From project root
python -m pytest tests/ -v

# From tests directory
python -m pytest . -v

# Run specific test file
python -m pytest test_basic.py -v

# Run with coverage
python -m pytest . --cov=backend --cov-report=html
```

## Test Coverage

### test_basic.py
- Language detection
- Document type classification  
- Field extraction
- Chunking
- RRF fusion
- HyDE query expansion

### test_processing.py
- PII redaction
- Language detection (detailed)
- Field extraction (detailed)
- Chunking with overlap

### test_retrieval.py
- BGE embedding generation
- FAISS indexing and search
- RRF fusion (detailed)
- Cross-encoder reranking
- HyDE expansion

### test_integration.py
- End-to-end PDF processing
- Multilingual documents
- PII redaction preservation
- Chunking with overlap verification
- Error handling
- Async database operations

## Dependencies

Basic tests require:
- Python 3.8+
- Core backend modules

Full test suite requires:
- All dependencies from `backend/requirements.txt`
- pytest
- pytest-asyncio
- PostgreSQL (for integration tests)

## Environment Setup

1. Install dependencies:
```bash
pip install -r backend/requirements.txt
pip install pytest pytest-asyncio
```

2. Set up environment:
```bash
cp .env.example .env
# Edit .env with your database settings
```

3. Initialize database:
```bash
cd backend
python -m utils.init_db
```

## Test Data

The tests use:
- `test_contract.pdf` - Sample contract for integration tests
- Programmatically generated test data
- Temporary files (automatically cleaned up)

## Writing New Tests

1. Add test functions to appropriate test file
2. Use descriptive test names starting with `test_`
3. Use fixtures from `conftest.py` when needed
4. Follow the existing pattern for assertions

Example:
```python
def test_new_feature(self):
    """Test new feature description."""
    result = function_under_test()
    assert result is not None
    assert result.property == expected_value
```

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError**: Ensure backend is in Python path
   - Tests automatically add `../backend` to sys.path

2. **Database connection errors**: Check DATABASE_URL in .env
   - Tests use async sessions from utils.database

3. **Missing models**: Some AI models download on first run
   - Allow time for initial downloads
   - Check HF_CACHE_DIR environment variable

### Running Tests Without Database

Some tests require PostgreSQL. To skip these:
```bash
python -m pytest . -k "not async" -v
```

### Debugging Failed Tests

Run with verbose output and shorter traceback:
```bash
python -m pytest . -v --tb=short
```

Or run a specific test:
```bash
python -m pytest test_basic.py::TestBasicFunctionality::test_language_detection -v -s
```

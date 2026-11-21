# Contributing to AapleSeva

Thank you for your interest in contributing to AapleSeva!

## Development Workflow

### Feature Branch Workflow

We follow a standard Git feature branch workflow:

1. **Create a feature branch from `main`**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write code
   - Add tests
   - Update documentation
   - Follow code style (use `ruff`)

3. **Test locally**
   ```bash
   cd Training
   
   # Run tests
   python -m pytest tests/ -v
   
   # Check linting
   ruff check .
   
   # Fix auto-fixable issues
   ruff check . --fix
   
   # Test Docker build
   docker build -f Dockerfile -t test-api .
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   
   # Use conventional commits:
   # feat: new feature
   # fix: bug fix
   # docs: documentation
   # test: add tests
   # refactor: code refactoring
   # chore: maintenance
   ```

5. **Push to GitHub**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create Pull Request**
   - Go to GitHub repository
   - Click "Compare & pull request"
   - Fill in PR template:
     - **Title**: Brief description
     - **Description**: What changed and why
     - **Testing**: How you tested it
     - **Screenshots**: If UI changes
   - Link any related issues

7. **Wait for CI to pass** ✅
   - GitHub Actions will run:
     - Ruff linting
     - pytest tests
     - Docker builds
   - All checks must pass before merge
   - PR will show green checkmarks

8. **Code Review**
   - Wait for maintainer review
   - Address feedback if requested
   - Push additional commits to same branch

9. **Merge**
   - Once approved and CI is green
   - Use "Squash and merge" (preferred)
   - Delete feature branch after merge

---

## Code Style

### Python
- **Formatter**: Ruff
- **Line length**: 88
- **Style**: PEP 8
- **Type hints**: Encouraged
- **Docstrings**: Required for public functions

### Running Ruff
```bash
# Check for issues
ruff check .

# Auto-fix
ruff check . --fix

# Format code
ruff format .
```

### Pre-commit (Optional)
Install pre-commit hooks to auto-check before committing:
```bash
pip install pre-commit
pre-commit install
```

---

## Testing

### Writing Tests
- Add tests for new features in `tests/`
- Use pytest fixtures from `conftest.py`
- Mock external dependencies (LLM, HTTP)
- Test both success and error cases

### Example Test
```python
import os
os.environ["LLM_MOCK"] = "1"

from app.mymodule import my_function

def test_my_function():
    """Test my_function returns expected result."""
    result = my_function("input")
    assert result["status"] == "ok"
    assert "data" in result
```

### Running Tests
```bash
# All tests
python -m pytest tests/ -v

# Specific file
python -m pytest tests/test_api.py -v

# With coverage
python -m pytest tests/ --cov=app --cov-report=html

# Fast tests only (if markers set)
python -m pytest tests/ -m "not slow"
```

---

## Documentation

### What to Document
- New features: Add to README.md
- API endpoints: Update OpenAPI docstrings
- Complex logic: Add inline comments
- Configuration: Update .env.example

### Documentation Style
- Use markdown
- Keep it concise
- Include code examples
- Add diagrams for complex flows

---

## Pull Request Guidelines

### PR Title
Use conventional commit format:
```
feat: add user authentication
fix: resolve API timeout issue
docs: update deployment guide
test: add tests for chunking module
```

### PR Description Template
```markdown
## What
Brief description of what changed.

## Why
Explanation of why this change is needed.

## How
Technical details of how it was implemented.

## Testing
- [ ] Added new tests
- [ ] All existing tests pass
- [ ] Tested locally with Docker
- [ ] Tested API endpoints

## Screenshots
(If UI changes)

## Checklist
- [ ] Code follows style guidelines (ruff check passes)
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No breaking changes (or documented if yes)
```

---

## Commit Message Guidelines

### Format
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **test**: Test additions/changes
- **refactor**: Code refactoring
- **chore**: Maintenance tasks
- **ci**: CI/CD changes

### Examples
```bash
feat(api): add POST /agent endpoint for agentic RAG

Implements LangGraph-based agent that can:
- Use rag_search tool for document questions
- Use rts_due_date tool for deadline calculations
- Maintain conversation memory across turns

Closes #42
```

```bash
fix(ui): resolve appeal ladder date calculation

Working days calculation was not accounting for Maharashtra holidays.
Added HOLIDAYS_2026 and HOLIDAYS_2027 constants.

Fixes #38
```

---

## CI/CD Pipeline

### GitHub Actions Workflows

#### CI Workflow (`.github/workflows/ci.yml`)
Runs on every push and PR:
1. **Lint**: Ruff check
2. **Test**: pytest with coverage
3. **Docker**: Build API and UI images
4. **Status**: Overall pass/fail

#### Deploy Workflow (`.github/workflows/deploy-render.yml`)
Runs on push to `main`:
- Triggers Render deployment hook
- Only if `RENDER_DEPLOY_HOOK` secret is configured

### Viewing CI Results
- Check PR page for status checks
- Click "Details" to see logs
- All checks must be green ✅ before merge

### Fixing CI Failures
```bash
# Linting failed
ruff check . --fix
git commit -am "fix: resolve linting issues"
git push

# Tests failed
python -m pytest tests/ -v  # Run locally to debug
# Fix the issue
git commit -am "fix: resolve test failures"
git push

# Docker build failed
docker build -f Dockerfile -t test .  # Build locally
# Fix Dockerfile or dependencies
git commit -am "fix: resolve Docker build"
git push
```

---

## Release Process

### Versioning
We use semantic versioning: `MAJOR.MINOR.PATCH`
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

### Creating a Release
1. Ensure `main` is stable (all CI passing)
2. Update version in relevant files
3. Create git tag:
   ```bash
   git tag -a v1.2.0 -m "Release v1.2.0: Add agent system"
   git push origin v1.2.0
   ```
4. Create GitHub Release with changelog

---

## Getting Help

- **Issues**: Open a GitHub issue for bugs/features
- **Discussions**: Use GitHub Discussions for questions
- **Email**: Contact maintainers (if provided in README)

---

## Code of Conduct

Be respectful, constructive, and collaborative. We follow the standard open-source code of conduct.

---

## License

By contributing, you agree that your contributions will be licensed under the project's MIT License.

---

Thank you for contributing to AapleSeva! 🙏

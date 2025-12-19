# GitHub Actions & Projects Quick Start

## 5-Minute Setup

### 1. Update Workflow Configuration
Edit `.github/workflows/project-automation.yml` and replace:
```yaml
project-url: https://github.com/YOUR_USERNAME/daily-market-tips/projects/1
```

### 2. Create GitHub Projects Board
1. Go to your repo → Projects tab
2. Click "New project" → "Table" layout
3. Name it "Development Board"
4. Note the project number from the URL

### 3. Sync Dependencies Locally
```bash
uv sync
```

This installs the new dev tools:
- `ruff` - Fast Python linter
- `mypy` - Type checker
- `pytest-cov` - Coverage reporting
- `bandit` - Security scanner

### 4. Test Locally
```bash
# Lint
uv run ruff check src/ tests/

# Type check
uv run mypy src/ --ignore-missing-imports

# Tests with coverage
uv run pytest tests/ -v --cov=src
```

### 5. Push and Watch
Push a commit and watch workflows run in the Actions tab.

## What Happens Automatically

### On Every Push/PR
✅ Linting with ruff  
✅ Type checking with mypy  
✅ Unit tests with pytest  
✅ Frontend build and tests  
✅ Security scanning  
✅ Coverage reporting  

### On Issue/PR Creation
✅ Auto-added to project board  
✅ Status set to "Backlog" (issues) or "In Review" (PRs)  

### Weekly
✅ Dependency updates via Dependabot  
✅ Stale issues/PRs marked and closed  

## Common Commands

### Before Committing
```bash
# Fix formatting issues
uv run ruff format src/ tests/

# Check for issues
uv run ruff check src/ tests/ --fix

# Type check
uv run mypy src/ --ignore-missing-imports

# Run tests
uv run pytest tests/ -v
```

### Viewing Results
- **CI Status**: Actions tab → CI workflow
- **Coverage**: Codecov.io (after setup)
- **Project Board**: Projects tab → Development Board
- **Dependencies**: Dependabot alerts in Security tab

## Troubleshooting

### Workflow Failed
1. Click the failed workflow in Actions tab
2. Expand the failed job
3. Look for error messages
4. Run the same command locally to debug

### Tests Failing
```bash
# Run locally first
uv run pytest tests/ -v

# Run specific test
uv run pytest tests/test_analysis_engine.py -v

# Run with more details
uv run pytest tests/ -vv --tb=long
```

### Linting Issues
```bash
# Auto-fix what you can
uv run ruff format src/ tests/
uv run ruff check src/ tests/ --fix

# See remaining issues
uv run ruff check src/ tests/
```

## Next Steps

1. ✅ Update project URL in workflows
2. ✅ Create GitHub Projects board
3. ⬜ Set up branch protection rules (Settings → Branches)
4. ⬜ Configure Codecov (codecov.io)
5. ⬜ Add status badges to README

## Documentation

- **Workflows**: See `.github/WORKFLOWS.md`
- **Projects**: See `.github/PROJECTS_SETUP.md`
- **Configuration**: See `pyproject.toml` for tool settings

## Key Files

```
.github/
├── workflows/
│   ├── ci.yml                    # Main CI/CD pipeline
│   ├── quality.yml               # Security & dependency checks
│   └── project-automation.yml    # Project board automation
├── dependabot.yml                # Dependency updates
├── WORKFLOWS.md                  # Detailed workflow docs
├── PROJECTS_SETUP.md             # Project board setup
└── QUICK_START.md                # This file
```

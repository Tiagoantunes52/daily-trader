# GitHub Actions Workflows

This project uses GitHub Actions for continuous integration, code quality checks, and project automation.

## Workflows Overview

### CI Workflow (`ci.yml`)
Runs on every push to `main`/`develop` and all pull requests.

**Backend Jobs:**
- Python 3.12 environment setup
- Dependency installation with `uv`
- Linting with ruff
- Format checking with ruff
- Type checking with mypy
- Unit tests with pytest
- Coverage reporting to Codecov

**Frontend Jobs:**
- Node.js 18 environment setup
- Dependency installation with npm
- Linting (if configured)
- Build verification
- Unit tests with vitest
- Coverage reporting to Codecov

**Triggers:**
- Push to `main` or `develop`
- Pull requests to `main` or `develop`

**Status Badges:**
Add to your README:
```markdown
[![CI](https://github.com/YOUR_USERNAME/daily-market-tips/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/daily-market-tips/actions/workflows/ci.yml)
```

### Code Quality Workflow (`quality.yml`)
Runs security and dependency checks.

**Jobs:**
- **Security**: Bandit security scanning for Python code
- **Dependency Check**: Identifies outdated dependencies
- **Frontend Security**: npm audit for vulnerabilities

**Triggers:**
- Push to `main` or `develop`
- Pull requests to `main` or `develop`

**Output:**
- Security reports uploaded as artifacts
- Audit results visible in workflow logs

### Project Automation Workflow (`project-automation.yml`)
Automatically manages GitHub Projects board.

**Jobs:**
- **Add to Project**: Adds new issues and PRs to project board
- **Update Status**: Comments on PRs with status updates
- **Close Stale**: Automatically closes inactive issues/PRs

**Triggers:**
- Issue opened or reopened
- PR opened, reopened, or marked ready for review
- PR review submitted

**Configuration:**
Update the project URL in the workflow file:
```yaml
project-url: https://github.com/YOUR_USERNAME/daily-market-tips/projects/1
```

### Dependabot Configuration (`dependabot.yml`)
Automatically creates PRs for dependency updates.

**Schedules:**
- Python dependencies: Weekly on Monday at 3 AM UTC
- Frontend dependencies: Weekly on Monday at 3 AM UTC
- GitHub Actions: Weekly on Monday at 3 AM UTC

**Features:**
- Limits to 5 open PRs per ecosystem
- Auto-labels with `dependencies` and ecosystem type
- Includes scope in commit messages
- Reviewers can be configured

**Configuration:**
Update the `reviewers` field with your GitHub username:
```yaml
reviewers:
  - "your-username"
```

## Local Development

### Running Checks Locally

Before pushing, run these commands to catch issues early:

**Linting:**
```bash
uv run ruff check src/ tests/
```

**Format Check:**
```bash
uv run ruff format --check src/ tests/
```

**Type Check:**
```bash
uv run mypy src/ --ignore-missing-imports
```

**Tests:**
```bash
uv run pytest tests/ -v --cov=src
```

**Security Check:**
```bash
uv run bandit -r src/
```

**Frontend:**
```bash
cd frontend
npm run lint
npm run build
npm run test:run
```

### Pre-commit Hook (Optional)

Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash
set -e

echo "Running linting..."
uv run ruff check src/ tests/

echo "Running type check..."
uv run mypy src/ --ignore-missing-imports || true

echo "Running tests..."
uv run pytest tests/ -v

echo "✅ All checks passed!"
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

## Troubleshooting

### CI Workflow Failures

**Ruff Linting Errors:**
- Run `uv run ruff check src/ tests/ --fix` to auto-fix
- Review remaining issues and fix manually

**Type Check Failures:**
- Add type hints to functions
- Use `# type: ignore` for known issues (sparingly)
- Check mypy output for specific errors

**Test Failures:**
- Run tests locally: `uv run pytest tests/ -v`
- Check test output for specific failures
- Ensure all dependencies are installed: `uv sync`

**Coverage Issues:**
- Ensure tests cover new code paths
- Check coverage report: `uv run pytest tests/ --cov=src --cov-report=html`
- Open `htmlcov/index.html` to view detailed coverage

### Frontend Build Failures

**Node Modules Issues:**
- Delete `node_modules` and `package-lock.json`
- Run `npm ci` to reinstall
- Check for conflicting dependencies

**Build Errors:**
- Run `npm run build` locally to debug
- Check for TypeScript errors
- Verify all imports are correct

### Workflow Not Running

**Check:**
1. Workflow file syntax (YAML validation)
2. Branch name matches trigger conditions
3. Workflow is enabled in Actions tab
4. No syntax errors in workflow file

**Debug:**
- View workflow logs in Actions tab
- Check for error messages in job output
- Verify environment variables are set

### Codecov Integration

**Setup:**
1. Go to https://codecov.io
2. Sign in with GitHub
3. Authorize Codecov
4. Select your repository
5. Codecov will automatically detect coverage reports

**Troubleshooting:**
- Ensure coverage files are generated: `--cov-report=xml`
- Check that upload step completes successfully
- Verify repository is public or Codecov token is configured

## Performance Tips

1. **Cache Dependencies**: Workflows cache npm and pip dependencies
2. **Matrix Strategy**: Python and Node versions run in parallel
3. **Conditional Steps**: Some steps only run on specific events
4. **Artifact Upload**: Only upload when necessary

## Security

- Workflows use `actions/checkout@v4` (latest stable)
- GitHub token is automatically provided and scoped
- No secrets are logged in workflow output
- Bandit scans for security issues in code

## Next Steps

1. Update project URL in `project-automation.yml`
2. Configure Codecov integration
3. Add status badges to README
4. Set up branch protection rules
5. Configure Dependabot reviewers
6. Create GitHub Projects board

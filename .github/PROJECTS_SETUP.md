# GitHub Projects Setup Guide

This guide walks you through setting up GitHub Projects for automated workflow management.

## Step 1: Create a New Project

1. Go to your repository on GitHub
2. Click the "Projects" tab
3. Click "New project"
4. Choose "Table" layout
5. Name it "Development Board"
6. Click "Create project"

## Step 2: Configure Project Fields

Add these custom fields to your project:

### Status (Single select)
- Backlog
- In Progress
- In Review
- Done
- Blocked

### Priority (Single select)
- Critical
- High
- Medium
- Low

### Type (Single select)
- Feature
- Bug
- Enhancement
- Documentation
- Chore

### Effort (Single select)
- XS (1-2 hours)
- S (2-4 hours)
- M (4-8 hours)
- L (8-16 hours)
- XL (16+ hours)

## Step 3: Set Up Automation Rules

### Auto-add Issues
1. Go to Project Settings → Automation
2. Click "Add workflow"
3. Select "Issues opened"
4. Set Status to "Backlog"

### Auto-add Pull Requests
1. Click "Add workflow"
2. Select "Pull requests opened"
3. Set Status to "In Review"

### Auto-move to Done
1. Click "Add workflow"
2. Select "Pull requests merged"
3. Set Status to "Done"

### Auto-close Stale Items
The `project-automation.yml` workflow handles this automatically.

## Step 4: Update Workflow Configuration

In `.github/workflows/project-automation.yml`, update the project URL:

```yaml
project-url: https://github.com/YOUR_USERNAME/daily-market-tips/projects/1
```

Replace:
- `YOUR_USERNAME` with your GitHub username
- `1` with your actual project number (visible in the URL)

## Step 5: Configure Branch Protection Rules

1. Go to Settings → Branches
2. Add rule for `main` branch:
   - Require pull request reviews before merging
   - Require status checks to pass (select all CI workflows)
   - Require branches to be up to date before merging
   - Include administrators

3. Add rule for `develop` branch:
   - Require pull request reviews before merging
   - Require status checks to pass

## Workflow Overview

### Issue Lifecycle
```
Issue Created → Backlog → In Progress → In Review → Done
```

### PR Lifecycle
```
PR Opened → In Review → (Changes Requested) → In Review → Merged → Done
```

### Stale Item Handling
- Issues: Marked stale after 30 days, closed after 7 more days
- PRs: Marked stale after 14 days, closed after 3 more days
- Exempt: Issues/PRs with `pinned` or `security` labels

## Best Practices

1. **Use Labels**: Tag issues with type, priority, and area
2. **Link PRs to Issues**: Use "Closes #123" in PR description
3. **Update Status**: Keep project board in sync with actual work
4. **Review Regularly**: Check for stale items weekly
5. **Prioritize**: Use Priority field to guide work order

## Useful Filters

Create saved views in your project:

### High Priority Work
```
Priority = "Critical" OR Priority = "High"
Status != "Done"
```

### Ready to Start
```
Status = "Backlog"
Priority = "High"
```

### In Progress
```
Status = "In Progress"
```

### Blocked Items
```
Status = "Blocked"
```

## Troubleshooting

### Workflows Not Running
- Check that the project URL is correct in `project-automation.yml`
- Verify the workflow file syntax with `yamllint`
- Check Actions tab for workflow errors

### Items Not Auto-Adding
- Ensure automation rules are enabled in project settings
- Check that the issue/PR matches the automation criteria
- Manually add items if automation fails

### Stale Workflow Not Working
- Verify the workflow is enabled in Actions
- Check that labels are spelled correctly
- Review the stale workflow logs in Actions tab

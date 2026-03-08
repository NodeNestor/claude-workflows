#!/bin/bash
# Install claude-workflows plugin — creates .claude/workflows/ in cwd
set -e

echo "Installing claude-workflows..."

# Create workflows directory in the current project
mkdir -p .claude/workflows/runs

echo "Created .claude/workflows/"
echo ""
echo "To get started, create a workflow file:"
echo "  .claude/workflows/my-workflow.yml"
echo ""
echo "Example:"
echo "  name: my-workflow"
echo "  description: What this workflow does"
echo "  trigger:"
echo "    event: PostToolUse"
echo "    matcher: Bash"
echo "  steps:"
echo "    - name: my-step"
echo "      run: echo hello"
echo ""
echo "See examples/ in the plugin directory for more."
echo "Done!"

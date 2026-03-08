# Install claude-workflows plugin — creates .claude/workflows/ in cwd
Write-Host "Installing claude-workflows..."

New-Item -ItemType Directory -Force -Path ".claude/workflows/runs" | Out-Null

Write-Host "Created .claude/workflows/"
Write-Host ""
Write-Host "To get started, create a workflow file:"
Write-Host "  .claude/workflows/my-workflow.yml"
Write-Host ""
Write-Host "Example:"
Write-Host "  name: my-workflow"
Write-Host "  description: What this workflow does"
Write-Host "  trigger:"
Write-Host "    event: PostToolUse"
Write-Host "    matcher: Bash"
Write-Host "  steps:"
Write-Host "    - name: my-step"
Write-Host "      run: echo hello"
Write-Host ""
Write-Host "See examples/ in the plugin directory for more."
Write-Host "Done!"

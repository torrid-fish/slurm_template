# SLURM Template

Tool suite for submitting jobs to SLURM, designed for machine learning workflows.

## Installation

```bash
git clone https://github.com/torrid-fish/slurm_template.git ~/.slurm_template
# Add to .bashrc or .zshrc
export PATH="~/.slurm_template/bin:$PATH"
```

## Tools

### `ssubmit`: Enhanced SLURM Job Submission

**Features:**
- Code version isolation: Creates automatic code snapshots (git worktree) for each job submission
- Data sharing: Shares large directories (data, checkpoints, etc.) via symlinks
- Parameterized configuration: Specify SLURM parameters without writing batch scripts
- Auto-cleanup: Cleans up snapshots on submission failure
- Unified log management: Automatically manages log directories

**Usage:**
Use as a drop-in replacement for `sbatch`:

```bash
ssubmit -N 1 -n 1 -p mi3001x \
    --time=05:00:00 \
    bash src/run_truthfulqa.sh
```

**Directory Structure**: The whole project is organized as follows:

```text
.
├── project_root/
│   ├── .git/          # Git data
│   ├── .venv/         # Virtual environment
│   ├── data/          # Large datasets
│   ├── checkpoints/   # Model checkpoints
│   ├── wandb/         # Weights & Biases files
│   ├── output/        # Output files
│   └── src/           # Source code
├── snapshots/         # Auto-generated code snapshots
│   └── <job_id>/      # Individual job snapshots
│       └── ...        # Snapshot contents
└── logs/              # Centralized log storage
    └── <job_id>.out   # Job output logs
```

### `jstat`: Job status monitoring
 
A wrapper of `sacct` for easier job status checking.
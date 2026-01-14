# SLURM Template

Tool suite for submitting jobs to SLURM, designed for machine learning workflows.

## Installation

```bash
git clone https://github.com/torrid-fish/slurm_template.git ~/.slurm_template
# Add to .bashrc or .zshrc
export PATH="~/.slurm_template/bin:$PATH"
```

## Tools

### `ssubmit` - Enhanced SLURM Job Submission

**Features:**
- Code version isolation: Creates automatic code snapshots (git worktree) for each job submission
- Data sharing: Shares large directories (data, checkpoints, etc.) via symlinks
- Parameterized configuration: Specify SLURM parameters without writing batch scripts
- Auto-cleanup: Cleans up snapshots on submission failure
- Unified log management: Automatically manages log directories

**Usage:**

```bash
# Simple submission
ssubmit 'python train.py'

# Specify GPU
ssubmit --gres=gpu:h100:1 'python train.py'

# Multiple SLURM parameters
ssubmit -N 2 -n 4 --time=2-00:00:00 --gres=gpu:a100:2 'python train.py --batch_size=256'

# With virtual environment
ssubmit 'source .venv/bin/activate && python train.py'

# Complex commands
ssubmit 'bash -c "source .venv/bin/activate && python train.py --config config.yaml"'
```

**Common SLURM Options:**

| Option | Description | Example |
|--------|-------------|---------|
| `-N` | Number of nodes | `-N 2` |
| `-n` | Number of tasks | `-n 4` |
| `-c` | CPU cores per task | `-c 8` |
| `-p` | Partition name | `-p gpu_partition` |
| `--time` | Time limit | `--time=2-00:00:00` (2 days) |
| `--gres` | Generic resources (GPUs etc.) | `--gres=gpu:h100:2` |

## Directory Structure

Required directories (automatically created if missing):

```
project-root/
├── data/                 # Datasets (shared via symlink)
├── checkpoints/          # Model checkpoints (shared via symlink)
├── output/              # Results (shared via symlink)
├── wandb/               # Weights & Biases logs (shared via symlink)
├── .venv/               # Python virtual environment (shared via symlink)
├── train.py
└── ...
```

#!/bin/bash
# Usage: ssubmit [OPTIONS] [SLURM_OPTIONS] '<command_or_script>'

# Parse arguments: OPTIONS, SLURM options (start with -), then command
SLURM_OPTS=()
SCRIPT=""
AUTO_CLEANUP=false

while [[ $# -gt 0 ]]; do
    # Check for ssubmit-specific options
    if [[ "$1" == "--cleanup" ]]; then
        AUTO_CLEANUP=true
        shift
    # Check if this is a SLURM option (starts with - and isn't just a dash)
    elif [[ "$1" == -* && "$1" != "-" ]]; then
        SLURM_OPTS+=("$1")
        shift
    else
        # Everything else is the script/command
        SCRIPT="$@"
        break
    fi
done

# Check if script/command argument is provided
if [ -z "$SCRIPT" ]; then
    echo "Usage: ssubmit [OPTIONS] [SLURM_OPTIONS] '<command_or_script>'"
    echo ""
    echo "ssubmit options:"
    echo "  --cleanup           Automatically clean up worktree after job finishes (default: keep)"
    echo ""
    echo "Examples:"
    echo "  ssubmit 'python train.py'"
    echo "  ssubmit --cleanup -N 2 'python train.py'"
    echo "  ssubmit --cleanup --gres=gpu:h100:1 'python train.py'"
    echo ""
    echo "Common SLURM options:"
    echo "  -N NUM              Number of nodes"
    echo "  -n NUM              Number of tasks"
    echo "  -c NUM              CPUs per task"
    echo "  --time=D-HH:MM:SS   Time limit"
    echo "  --gres=TYPE:NUM     Generic resources (e.g., gpu:h100:1)"
    echo "  -p PARTITION        Partition name"
    exit 1
fi

# If script is a file, convert to absolute path
if [ -f "$SCRIPT" ]; then
    SCRIPT="$(cd "$(dirname "$SCRIPT")" && pwd)/$(basename "$SCRIPT")"
fi

if ! command -v git &> /dev/null; then
    echo "Git could not be found. Please install Git to use this script."
    exit 1
fi
# Get the absolute path of the current directory as the project root
HOST_PROJECT_ROOT="$(pwd)"

if [ -n "$(git status --porcelain)" ]; then
    echo "Dirty worktree detected. Please commit your changes first."
    echo "   (Git Worktree requires a clean commit to snapshot HEAD)"
    exit 1
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
GIT_HASH=$(git rev-parse --short HEAD 2>/dev/null || echo "nogit")
FULL_ID="${TIMESTAMP}_${GIT_HASH}"

HOST_SNAPSHOT_DIR="${HOME}/snapshots/${FULL_ID}"
mkdir -p "$HOST_SNAPSHOT_DIR"

# Setup cleanup trap for failed submissions
cleanup() {
    if [ $? -ne 0 ]; then
        echo "Cleaning up after error..."
        git worktree remove -f "$HOST_SNAPSHOT_DIR" 2>/dev/null || true
        rm -rf "$HOST_SNAPSHOT_DIR"
    fi
}
trap cleanup EXIT

echo "Creating code snapshot: $FULL_ID"
git worktree add --detach -f "$HOST_SNAPSHOT_DIR" HEAD > /dev/null

echo "Soft-linking data directories..."
DIRECTORIES=("data" "checkpoints" "output" "wandb" ".venv")
for DIR in "${DIRECTORIES[@]}"; do
    if [ -d "${HOST_PROJECT_ROOT}/${DIR}" ]; then
        mkdir -p "${HOST_SNAPSHOT_DIR}/${DIR}"
        ln -s "${HOST_PROJECT_ROOT}/${DIR}" "${HOST_SNAPSHOT_DIR}/${DIR}"
    fi
done

echo "Submitting job to SLURM..."
mkdir -p "${HOME}/log"

# Build sbatch command with default parameters and user-provided options
SBATCH_OPTS=(
    "-N 1"
    "-n 1"
    "-c 4"
    "-p p01"
    "--time=0-30:00:00"
    "--gres=gpu:h100:1"
    "--job-name=${FULL_ID}"
    "-o ${HOME}/log/${FULL_ID}.out"
    "$@"  # Append user-provided options (will override defaults)
)

sbatch "${SBATCH_OPTS[@]}" << EOF
#!/bin/bash

export SLURM_JOB_ID="${FULL_ID}"
export AUTO_CLEANUP="${AUTO_CLEANUP}"
export HOST_SNAPSHOT_DIR="${HOST_SNAPSHOT_DIR}"
export HOST_PROJECT_ROOT="${HOST_PROJECT_ROOT}"

echo "   Job ID: \$SLURM_JOB_ID"
echo "   Job started on node: \$(hostname)"
echo "   Running script: $(basename "$SCRIPT")"
echo "   Snapshot Context: \$HOST_SNAPSHOT_DIR"

# Cleanup callback
cleanup_worktree() {
    if [ "\$AUTO_CLEANUP" = "true" ]; then
        echo "   Cleaning up worktree: \$HOST_SNAPSHOT_DIR"
        # Exit worktree and return to project root before removing
        cd "\$HOST_PROJECT_ROOT"
        git worktree remove -f "\$HOST_SNAPSHOT_DIR" 2>/dev/null || true
        rm -rf "\$HOST_SNAPSHOT_DIR"
        echo "   Cleanup completed"
    else
        echo "   Worktree snapshot kept at: \$HOST_SNAPSHOT_DIR"
        echo "   To manually clean up: cd \$HOST_PROJECT_ROOT && git worktree remove -f \$HOST_SNAPSHOT_DIR && rm -rf \$HOST_SNAPSHOT_DIR"
    fi
}

# Register cleanup callback on exit
trap cleanup_worktree EXIT

cd "$HOST_SNAPSHOT_DIR"
"$SCRIPT"

EOF

echo "Job submitted! Log will be saved to ${HOME}/log/${FULL_ID}.out"
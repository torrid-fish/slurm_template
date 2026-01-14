#!/usr/bin/env python3
"""
SLURM sbatch command parser.

This module provides a clean, Pythonic way to parse and validate SLURM sbatch options,
replacing complex bash parsing logic with robust structured parsing.
"""

import argparse
import re
import sys
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any, Tuple


@dataclass
class SbatchOptions:
    """Parsed SLURM sbatch options."""
    
    # Resource allocation
    nodes: Optional[int] = None  # -N, --nodes
    ntasks: Optional[int] = None  # -n, --ntasks
    cpus_per_task: Optional[int] = None  # -c, --cpus-per-task
    
    # GPU/Generic resources
    gres: Optional[str] = None  # --gres
    
    # Time and partition
    time: Optional[str] = None  # --time
    partition: Optional[str] = None  # -p, --partition
    
    # Job naming and output
    job_name: Optional[str] = None  # -J, --job-name
    output: Optional[str] = None  # -o, --output
    error: Optional[str] = None  # -e, --error
    
    # Memory
    mem: Optional[str] = None  # --mem
    mem_per_cpu: Optional[str] = None  # --mem-per-cpu
    
    # Email notifications
    mail_type: Optional[str] = None  # --mail-type
    mail_user: Optional[str] = None  # --mail-user
    
    # Advanced options
    dependency: Optional[str] = None  # --dependency
    array: Optional[str] = None  # --array
    exclusive: Optional[str] = None  # --exclusive
    constraint: Optional[str] = None  # --constraint
    account: Optional[str] = None  # -A, --account
    
    # Raw options not explicitly supported
    extra_options: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self, exclude_none: bool = True, exclude_empty_extra: bool = True) -> Dict:
        """Convert to dictionary, optionally excluding None values."""
        result = asdict(self)
        if exclude_empty_extra:
            if not result.get("extra_options"):
                result.pop("extra_options")
        if exclude_none:
            result = {k: v for k, v in result.items() if v is not None}
        return result
    
    def to_sbatch_args(self) -> List[str]:
        """Convert back to sbatch command line arguments."""
        args = []
        
        mapping = {
            "nodes": ("--nodes", "="),
            "ntasks": ("--ntasks", "="),
            "cpus_per_task": ("--cpus-per-task", "="),
            "gres": ("--gres", "="),
            "time": ("--time", "="),
            "partition": ("--partition", "="),
            "job_name": ("--job-name", "="),
            "output": ("--output", "="),
            "error": ("--error", "="),
            "mem": ("--mem", "="),
            "mem_per_cpu": ("--mem-per-cpu", "="),
            "mail_type": ("--mail-type", "="),
            "mail_user": ("--mail-user", "="),
            "dependency": ("--dependency", "="),
            "array": ("--array", "="),
            "exclusive": ("--exclusive", "="),
            "constraint": ("--constraint", "="),
            "account": ("--account", "="),
        }
        
        for attr, (flag, sep) in mapping.items():
            value = getattr(self, attr)
            if value is not None:
                args.append(f"{flag}{sep}{value}")
        
        # Add extra options
        for key, value in self.extra_options.items():
            if value is True:
                args.append(f"--{key}")
            elif value is False:
                continue
            else:
                args.append(f"--{key}={value}")
        
        return args


class SbatchParser:
    """Parser for SLURM sbatch options."""
    
    # Known option aliases and their canonical forms
    OPTION_ALIASES = {
        "-N": "nodes",
        "--nodes": "nodes",
        "-n": "ntasks",
        "--ntasks": "ntasks",
        "-c": "cpus_per_task",
        "--cpus-per-task": "cpus_per_task",
        "--gres": "gres",
        "--time": "time",
        "-p": "partition",
        "--partition": "partition",
        "-J": "job_name",
        "--job-name": "job_name",
        "-o": "output",
        "--output": "output",
        "-e": "error",
        "--error": "error",
        "--mem": "mem",
        "--mem-per-cpu": "mem_per_cpu",
        "--mail-type": "mail_type",
        "--mail-user": "mail_user",
        "--dependency": "dependency",
        "--array": "array",
        "--exclusive": "exclusive",
        "--constraint": "constraint",
        "-A": "account",
        "--account": "account",
    }
    
    def __init__(self):
        self.options = SbatchOptions()
        self.errors: List[str] = []
    
    def parse(self, args: List[str]) -> Tuple[SbatchOptions, List[str]]:
        """
        Parse sbatch options from command line arguments.
        
        Args:
            args: Command line arguments (typically sys.argv[1:])
        
        Returns:
            Tuple of (SbatchOptions, remaining_args)
        """
        i = 0
        
        while i < len(args):
            arg = args[i]
            
            # If it's a non-option argument, everything from here on is the command
            if not arg.startswith("-"):
                return self.options, args[i:]
            
            # Handle -- to stop parsing (standard convention)
            if arg == "--":
                return self.options, args[i+1:]
            
            # Handle -h or --help
            if arg in ("-h", "--help"):
                self._print_help()
                sys.exit(0)
            
            # Parse option
            i = self._parse_option(arg, args, i, [])
        
        return self.options, []
    
    def _parse_option(self, arg: str, args: List[str], index: int, remaining: List[str]) -> int:
        """
        Parse a single option. Returns the new index.
        """
        # Handle --option=value format
        if "=" in arg:
            option, value = arg.split("=", 1)
            return self._set_option(option, value, index) + 1
        
        # Handle -option value or -option (flag) format
        if arg in self.OPTION_ALIASES:
            canonical = self.OPTION_ALIASES[arg]
            
            # Check if this option takes a value
            if self._option_takes_value(canonical):
                if index + 1 >= len(args):
                    self.errors.append(f"Option {arg} requires a value")
                    return index + 1
                
                next_arg = args[index + 1]
                if next_arg.startswith("-"):
                    self.errors.append(f"Option {arg} requires a value, got {next_arg}")
                    return index + 1
                
                return self._set_option(arg, next_arg, index) + 2
            else:
                # Flag-style option
                return self._set_option(arg, True, index) + 1
        
        # Unknown option - store as extra
        if "=" in arg:
            option, value = arg.split("=", 1)
            option_name = option.lstrip("-").replace("-", "_")
            self.options.extra_options[option_name] = value
        else:
            option_name = arg.lstrip("-").replace("-", "_")
            self.options.extra_options[option_name] = True
        
        return index + 1
    
    def _option_takes_value(self, canonical_name: str) -> bool:
        """Check if an option takes a value."""
        # These options are flags that don't take values
        flag_options = {"exclusive"}
        return canonical_name not in flag_options
    
    def _set_option(self, option: str, value: Any, index: int) -> int:
        """
        Set an option value. Returns the current index.
        """
        canonical = self.OPTION_ALIASES.get(option)
        
        if not canonical:
            # Unknown option, store as extra
            option_name = option.lstrip("-").replace("-", "_")
            self.options.extra_options[option_name] = value
            return index
        
        try:
            if canonical == "nodes":
                self.options.nodes = int(value)
            elif canonical == "ntasks":
                self.options.ntasks = int(value)
            elif canonical == "cpus_per_task":
                self.options.cpus_per_task = int(value)
            elif canonical == "gres":
                self.options.gres = str(value)
            elif canonical == "time":
                self._validate_time_format(value)
                self.options.time = str(value)
            elif canonical == "partition":
                self.options.partition = str(value)
            elif canonical == "job_name":
                self.options.job_name = str(value)
            elif canonical == "output":
                self.options.output = str(value)
            elif canonical == "error":
                self.options.error = str(value)
            elif canonical == "mem":
                self._validate_memory_format(value)
                self.options.mem = str(value)
            elif canonical == "mem_per_cpu":
                self._validate_memory_format(value)
                self.options.mem_per_cpu = str(value)
            elif canonical == "mail_type":
                self.options.mail_type = str(value)
            elif canonical == "mail_user":
                self.options.mail_user = str(value)
            elif canonical == "dependency":
                self.options.dependency = str(value)
            elif canonical == "array":
                self.options.array = str(value)
            elif canonical == "exclusive":
                self.options.exclusive = str(value) if isinstance(value, str) else ("user" if value else None)
            elif canonical == "constraint":
                self.options.constraint = str(value)
            elif canonical == "account":
                self.options.account = str(value)
        except ValueError as e:
            self.errors.append(f"Invalid value for {option}: {e}")
        
        return index
    
    def _validate_time_format(self, time_str: str) -> bool:
        """Validate SLURM time format (minutes, HH:MM:SS, or D-HH:MM:SS)."""
        # Format: [D-]HH:MM:SS or minutes (integer)
        if re.match(r"^\d+$", time_str):
            return True
        if re.match(r"^\d+-\d{1,2}:\d{2}:\d{2}$", time_str):
            return True
        if re.match(r"^\d{1,2}:\d{2}:\d{2}$", time_str):
            return True
        self.errors.append(f"Invalid time format: {time_str}. Use minutes, HH:MM:SS, or D-HH:MM:SS")
        return False
    
    def _validate_memory_format(self, mem_str: str) -> bool:
        """Validate SLURM memory format (e.g., 4G, 512M)."""
        if re.match(r"^\d+[KMGT]?$", mem_str, re.IGNORECASE):
            return True
        self.errors.append(f"Invalid memory format: {mem_str}. Use format like 4G, 512M, or 1024")
        return False
    
    @staticmethod
    def _print_help():
        """Print help message."""
        help_text = """
SLURM sbatch Option Parser

Usage:
    sbatch_parser.py [SBATCH_OPTIONS]

Common SLURM Options:
    Resource Allocation:
        -N, --nodes NUM                 Number of nodes
        -n, --ntasks NUM                Number of tasks
        -c, --cpus-per-task NUM         CPUs per task
        
    GPU/Generic Resources:
        --gres TYPE:NUM                 Generic resources (e.g., gpu:h100:1)
    
    Time and Partition:
        --time D-HH:MM:SS              Time limit
        -p, --partition NAME            Partition name
    
    Job Configuration:
        -J, --job-name NAME             Job name
        -o, --output FILE               Output file
        -e, --error FILE                Error file
    
    Memory:
        --mem SIZE                      Memory per node (e.g., 16G, 8192M)
        --mem-per-cpu SIZE              Memory per CPU
    
    Notifications:
        --mail-type TYPE                Mail notification type
        --mail-user EMAIL               Email address
    
    Advanced:
        --dependency DEPENDENCY_LIST    Job dependencies
        --array RANGE                   Job array range
        --exclusive [VALUE]             Exclusive node access
        --constraint CONSTRAINT         Resource constraints
        -A, --account ACCOUNT           Account name

Examples:
    Single node with GPU:
        sbatch_parser.py -N 1 --gres=gpu:1
    
    Multiple nodes:
        sbatch_parser.py -N 2 -n 4 --mem=32G
    
    With time limit:
        sbatch_parser.py --time=2-00:00:00 -c 8
"""
        print(help_text)
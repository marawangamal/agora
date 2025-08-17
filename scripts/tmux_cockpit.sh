#!/usr/bin/env bash
# tmux_cockpit.sh
#
# Usage:
#   ./tmux_cockpit.sh python train.py --epochs 10
#
# Optional flags BEFORE the work command:
#   --monitor "<cmd>"  override monitor command (default: combined CPU/GPU monitor)
#   --session NAME     tmux session name (default: dev)

set -euo pipefail

# ---- defaults ----------------------------------------------------------------
# Simple monitoring command with visual bars
MONITOR_CMD='bash -c "
while true; do 
  clear
  echo \"📊 System Monitor - \$(date +\"%H:%M:%S\")\"
  echo

  # Make bar function
  make_bar() {
    local pct=\$1
    local width=10
    local filled=\$((pct * width / 100))
    local empty=\$((width - filled))
    printf \"[\"
    for ((i=0; i<filled; i++)); do printf \"█\"; done
    for ((i=0; i<empty; i++)); do printf \"░\"; done
    printf \"] %3s%%\" \"\$pct\"
  }

  # Get system stats with SLURM awareness
  cpu_total=\$(top -bn1 | grep \"Cpu(s)\" | awk \"{print \\\$2}\" | sed \"s/%us,//\" | cut -d\".\" -f1)
  # Fallback if top parsing fails
  if [[ -z \"\$cpu_total\" || \"\$cpu_total\" == \"0\" ]]; then
    cpu_total=\$(grep \"cpu \" /proc/stat | awk \"{idle=\\\$5; total=\\\$2+\\\$3+\\\$4+\\\$5+\\\$6+\\\$7+\\\$8; print int((total-idle)*100/total)}\")
  fi
  
  # SLURM-aware memory reporting
  if [[ -n \"\${SLURM_MEM_PER_NODE:-}\" ]]; then
    # Use SLURM allocation
    slurm_mem_gb=\$((SLURM_MEM_PER_NODE / 1024))
    ram_used_kb=\$(free | awk \"NR==2{print \\\$3}\")
    ram_used_gb=\$((ram_used_kb / 1024 / 1024))
    ram_pct=\$((ram_used_gb * 100 / slurm_mem_gb))
    ram_used=\"\${ram_used_gb}G\"
    ram_total=\"\${slurm_mem_gb}G\"
  else
    # Fallback to system memory
    ram_pct=\$(free | awk \"NR==2{printf \\\"%d\\\", \\\$3/\\\$2*100}\")
    ram_used=\$(free -h | awk \"NR==2{print \\\$3}\")
    ram_total=\$(free -h | awk \"NR==2{print \\\$2}\")
  fi
  
  # SLURM CPU info
  if [[ -n \"\${SLURM_CPUS_PER_TASK:-}\" ]]; then
    slurm_cpus=\$SLURM_CPUS_PER_TASK
  else
    slurm_cpus=8  # Default fallback
  fi

  echo \"💻 CPUs: (showing \$slurm_cpus cores)\"
  # Show allocated CPUs from SLURM with actual per-CPU usage
  for ((i=0; i<slurm_cpus && i<8; i++)); do
    # Get per-CPU usage from /proc/stat
    cpu_usage=\$(awk \"/^cpu\$i / {idle=\\\$5; total=\\\$2+\\\$3+\\\$4+\\\$5+\\\$6+\\\$7+\\\$8; if(total>0) print int((total-idle)*100/total); else print 0}\" /proc/stat)
    if [[ -z \"\$cpu_usage\" ]]; then cpu_usage=0; fi
    
    printf \"  CPU\$i: \"
    make_bar \$cpu_usage
    printf \" | RAM: \"
    make_bar 0
    printf \"\\n\"
  done

  echo
  echo \"🎮 GPUs:\"
  if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi --query-gpu=index,utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader,nounits | while read line; do
      IFS=\",\" read -r idx gpu_util mem_used mem_total temp <<< \"\$line\"
      vram_pct=\$((mem_used * 100 / mem_total))
      printf \"  GPU\$idx: \"
      make_bar \$gpu_util
      printf \" | VRAM: \"
      make_bar \$vram_pct
      printf \" | %s°C\\n\" \$temp
    done
  fi

  echo
  echo \"📊 Totals:\"
  
  # CPU and RAM totals
  printf \"  CPU: \"
  make_bar \$cpu_total
  printf \" | RAM: \"
  make_bar \$ram_pct
  if [[ -n \"\${SLURM_MEM_PER_NODE:-}\" ]]; then
    printf \" (\$ram_used/\$ram_total SLURM)\\n\"
  else
    printf \" (\$ram_used/\$ram_total)\\n\"
  fi
  
  # GPU totals
  if command -v nvidia-smi >/dev/null 2>&1; then
    gpu_avg=\$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits | awk \"{sum+=\\\$1; count++} END {printf \\\"%d\\\", sum/count}\")
    vram_used_gb=\$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | awk \"{sum+=\\\$1} END {printf \\\"%d\\\", sum/1024}\")
    vram_total_gb=\$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | awk \"{sum+=\\\$1} END {printf \\\"%d\\\", sum/1024}\")
    vram_pct_total=\$((vram_used_gb * 100 / vram_total_gb))
    
    printf \"  GPU: \"
    make_bar \$gpu_avg
    printf \" | VRAM: \"
    make_bar \$vram_pct_total
    printf \" (\${vram_used_gb}G/\${vram_total_gb}G)\\n\"
  fi
  
  # Load and disk
  load=\$(uptime | awk -F\"load average:\" \"{print \\\$2}\" | sed \"s/^ *//\")
  disk=\$(df -h / | awk \"NR==2{printf \\\"%s/%s (%s)\\\", \\\$3,\\\$2,\\\$5}\")
  
  echo \"  Load:\$load\"
  echo \"  Disk: \$disk\"
  
  sleep 2
done
"'

SESSION="dev"

# ---- parse overrides ---------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --monitor)  MONITOR_CMD="$2"; shift 2 ;;
    --session)  SESSION="$2";     shift 2 ;;
    --)         shift; break ;;             # explicit end of flags
    *)          break ;;                    # first non-flag = start of work cmd
  esac
done

if [[ $# -eq 0 ]]; then
  echo "Error: you must supply the command to run in the left pane."
  echo "Example: $0 python train.py --epochs 10"
  echo ""
  echo "Available monitor overrides:"
  echo "  --monitor 'htop'                    # CPU only"
  echo "  --monitor 'watch -n1 nvidia-smi'   # GPU only"
  echo "  --monitor 'nvtop'                  # GPU interactive"
  exit 1
fi
WORK_CMD="$*"

# ---- launch / attach ---------------------------------------------------------
if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "[tmux-cockpit] Attaching to existing session '$SESSION'..."
  tmux attach -t "$SESSION"
  exit
fi

echo "[tmux-cockpit] Creating session '$SESSION'..."
tmux new-session  -d -s "$SESSION"              # pane 0 (left - work pane)
tmux send-keys    -t "$SESSION":0.0 "$WORK_CMD" C-m

tmux split-window -h -p 20                      # pane 1 (right - monitor pane)
tmux send-keys    -t "$SESSION":0.1 "$MONITOR_CMD" C-m

tmux select-pane  -t "$SESSION":0.0             # put focus back on work pane
tmux attach       -t "$SESSION"
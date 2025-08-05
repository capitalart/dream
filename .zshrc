# ~/.zshrc — DreamArtMachine Auto Environment Setup

# Set default working directory (optional)
cd /home/dream

# Auto-activate DreamArtMachine venv
if [ -d "/home/dream/venv" ]; then
  source /home/dream/venv/bin/activate
fi

# Optional: custom prompt
export PS1="(venv) \u@\h:\w\$ "

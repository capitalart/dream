# ~/.bashrc: Enhanced and robust for a developer workflow.

# If not running interactively, don't do anything
case $- in
    *i*) ;;
      *) return;;
esac

# ============================================================================
# 1. HISTORY CONTROL
# ============================================================================
HISTCONTROL=ignoreboth
shopt -s histappend
HISTSIZE=10000
HISTFILESIZE=20000

# ============================================================================
# 2. GIT-AWARE PROMPT
# ============================================================================
# Function to parse Git branch and status
parse_git_branch() {
    git branch 2> /dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/ (\1)/'
}
parse_git_dirty() {
    # Check for unstaged changes, staged changes, or untracked files
    if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null || [ -n "$(git ls-files --others --exclude-standard)" ]; then
        echo "*"
    fi
}

# --- Safety check for color support ---
color_prompt=
case "$TERM" in
    xterm-color|*-256color) color_prompt=yes;;
esac

if [ "$color_prompt" = yes ]; then
    # Set a colorful prompt for supported terminals
    PS1='\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\[\033[01;33m\]$(parse_git_branch)\[\033[01;31m\]$(parse_git_dirty)\[\033[00m\]\$ '
else
    # Set a plain, non-colored prompt but keep the Git info
    PS1='\u@\h:\w$(parse_git_branch)$(parse_git_dirty)\$ '
fi
unset color_prompt

# ============================================================================
# 3. USEFUL ALIASES
# ============================================================================
alias ls='ls --color=auto -F' # Add file type indicators (e.g., / for directories)
alias ll='ls -alF'             # Long listing format
alias la='ls -A'               # List all files except . and ..
alias grep='grep --color=auto'
alias ..='cd ..'               # Go up one directory
alias ...='cd ../..'           # Go up two directories

# ============================================================================
# 4. HELPER FUNCTIONS
# ============================================================================
# Function to create a directory and then change into it
mkcd() {
    mkdir -p "$1" && cd "$1"
}

# ============================================================================
# 5. SHELL COMPLETION & ENVIRONMENT
# ============================================================================
if ! shopt -oq posix; then
  if [ -f /usr/share/bash-completion/bash_completion ]; then
    . /usr/share/bash-completion/bash_completion
  elif [ -f /etc/bash_completion ]; then
    . /etc/bash_completion
  fi
fi

# ============================================================================
# 6. CUSTOM ACTIVATIONS
# ============================================================================
# Auto-activate project venv for DreamArtMachine
if [ -f "/home/dream/venv/bin/activate" ]; then
    source /home/dream/venv/bin/activate
fi

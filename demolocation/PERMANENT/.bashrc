test -r ~/.alias && . ~/.alias
PS1='GRASS 7.0.svn (demolocation):\w > '
PROMPT_COMMAND="'/home/neteler/grass70/dist.x86_64-unknown-linux-gnu/etc/prompt.py'"
# User specific aliases and functions
alias cp='cp -i'
alias mv='mv -i'
alias rm='rm -i'
alias df='df -h -x supermount'
alias du='du -h'
alias egrep='egrep --color'
alias fgrep='fgrep --color'
alias grep='grep --color'
alias l='ls -lrt --color=tty'
alias ls='ls -F --show-control-chars --color=auto'
alias vi='vim'
alias which='alias | /usr/bin/which --tty-only --read-alias --show-dot --show-tilde'
alias scpresume='rsync --partial --times --progress --rsh=ssh'
alias scpresume_compress='rsync --partial --times --progress --compress --rsh=ssh'
# http://vim.wikia.com/wiki/How_to_obscure_text_instantaneously
alias rot13="tr 'A-Za-z' 'N-ZA-Mn-za-m'"
export SVN_EDITOR=vim



export PATH="/home/neteler/grass70/dist.x86_64-unknown-linux-gnu/bin:/home/neteler/grass70/dist.x86_64-unknown-linux-gnu/scripts:/home/neteler/.grass7/addons/bin:/home/neteler/.grass7/addons/scripts:/usr/lib64/qt-3.3/bin:/usr/lib64/ccache:/usr/libexec/lightdm:/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/usr/sbin:/home/neteler/bin:/home/neteler/.local/bin:/home/neteler/bin:/usr/sbin:/home/neteler/bin"
export HOME="/home/neteler"

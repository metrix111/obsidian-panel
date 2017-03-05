#!/bin/sh

# constants
DIR=$(dirname $([ -L $0 ] && readlink -f $0 || echo $0))

# vars
_SUDO=""

_check_sudo() {
    if [[ "$EUID" -ne 0 ]]; then
        echo "[WARN] You have to run this script with root privilege. e.g. : sudo ./start-panel.sh"
        echo "[WARN] Since some operations in this script may require root privilege."
        echo "[WARN] If you have any question, you can ask your system administrator for help."
        echo ""
        exit 1
    fi
}

_realpath() {
    [[ $1 = /* ]] && echo "$1" || echo "$PWD/${1#./}"
}

_detect_dependency() {
    if command -v $1 >/dev/null 2>&1; then
        return 1
    else
        return 0
    fi
}

echo_bold() {
    echo -e "\033[1m"$1"\033[0m"
}

copy_ob_panel_command() {
    OB_PANEL_FILE="/usr/local/bin/ob-panel"
    $_SUDO rm -f $OB_PANEL_FILE

    $_SUDO ln -s $(_realpath ./binary/ob-panel.sh) $OB_PANEL_FILE
}

install_supervisor() {
    echo "Installing supervisor..."

    if [ -x "/usr/bin/apt-get" ]; then
        echo "pm: DPKG"
        $_SUDO apt-get install supervisor
    elif [ -x "/usr/bin/yum"]; then
        echo "pm: YUM"
        $_SUDO apt-get install supervisor
    else
        echo "Unsupported Package Manager type. You may have to install supervisor manually, sorry :-("
    fi
}

generate_supervisord_conf() {
    SUPERVISOR_DIR="/etc/supervisor.d"
    if [ -d $SUPERVISOR_DIR ]; then
        $_SUDO mkdir -p $SUPERVISOR_DIR
    fi

    CONF_FILE=$SUPERVISOR_DIR"/obsidian-panel.conf"

    # write empty data to config file
    $_SUDO echo "" > $CONF_FILE

    # write supervisor config
    $_SUDO cat >> $CONF_FILE <<- EOF
[supervisord]
logfile = /var/run/ob-panel-supervisord.log
logfile_maxbytes = 50MB
logfile_backups=10
loglevel = info
pidfile = /var/run/supervisord.pid
nodaemon = false

[supervisorctl]
serverurl = unix:///tmp/supervisor.sock
EOF

    # write program config
    for prog in app ftp_manager zeromq_broker task_manager process_watcher
    do
        $_SUDO cat >> $CONF_FILE <<- EOF
[program:$prog]
directory=$(_realpath ./bundle/obsidian-panel)
command=$(_realpath ./bundle/obsidian-panel) -b $prog
process_name=ob-panel-$prog
numprocs=1
startsecs=5
stopsignal=TERM
stopwaitsecs=10
user=root
stdout_logfile=/var/log/ob-panel.log
stderr_logfile=/var/log/ob-panel.log

EOF
    done
}

echo -e ""
echo_bold "Welcome To Obsidian-Panel!"
echo_bold "=========================="

_check_sudo

echo_bold "a. Check 'ob-panel' command..."
copy_ob_panel_command
echo_bold "b. Check supervisor availablity..."
_detect_dependency supervisord && install_supervisor

generate_supervisord_conf

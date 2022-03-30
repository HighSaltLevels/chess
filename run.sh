#!/bin/bash

if [[ -z $KUBERNETES_SERVICE_HOST || -z $KUBERNETES_SERVICE_PORT ]]; then
    echo "'KUBERNETES_SERVICE_HOST' and 'KUBERNETES_SERVICE_PORT' environment"
    echo "variables were not set. If you are running this as a developer,"
    echo "set these environment variables to a valid kubernentes hostname"
    echo "and port."
    exit 1
fi

if [[ ! -f "/var/run/secrets/kubernetes.io/serviceaccount/token" || \
      ! -f "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt" ]]; then
    echo "Failed to locate service account token. If you are running this"
    echo "as a developer, write a service account token to:"
    echo "'/var/run/secrets/kubernetes.io/serviceaccount/token' that has"
    echo "permission to manage chess-game Custom Resources, as well as a"
    echo "CA Certificate for this cluster at:"
    echo "'/var/run/secrets/kubernetes.io/serviceaccount/ca.crt'"
    exit 1
fi

# Make sure tmux and stockfish are installed
for proc in "stockfish" "tmux"; do
    which ${proc} > /dev/null
    if [ $? -ne 0 ]; then
        echo "Missing dependency ${proc}"
        echo "Please install it using a package manager"
    fi
done

function cleanup {
    for session in $(tmux ls | grep stockfish | colrm 47); do
        tmux kill-session -t $session
    done
    rm -f /tmp/stockfish*.log
}

trap cleanup EXIT

# Start the server
if [ -d "/opt/server" ]; then
    echo "Container environment detected."
    export PYTHONPATH=/opt/server
    exec gunicorn \
            --bind '0.0.0.0:8000' \
            --workers 5 \
            --worker-class gevent \
            --timeout 60 \
            'app:app()'
elif [ -d ".git" ]; then
    # Print a helper message for developers who may want to enable debug logging
    if [ -z ${DEBUG} ]; then
        echo "Debug logging is disabled. If you want to enable debug logging,"
        echo 'then set the "DEBUG" environment variable to true'
    fi

    # No need to exec in a developer environment so that trap,
    # can clean up the tmux sessions and log files.
    echo "Developer environment detected."
    export PYTHONPATH=$(pwd)/server
    gunicorn \
        --bind '0.0.0.0:8000' \
        --workers 2 \
        --worker-class gevent \
        --timeout 60 \
        'app:app()'
else
    echo "Failed to determine environment. If you are running"
    echo "this as a developer, please run this script from the"
    echo "project directory. If this is in a container, then"
    echo "something is wrong with the integrity of this container."
    exit 1
fi

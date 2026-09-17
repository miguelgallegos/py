# set conditional execution for the script
# if param is build run line 5 if param is run run line 6
set -e

if [ "$1" = "build" ]; then
    docker build -t trading-api .
elif [ "$1" = "run" ]; then
    docker run --rm -p 5002:5002 --env-file .env trading-api
else
    echo "Usage: $0 {build|run}"
    exit 1
fi

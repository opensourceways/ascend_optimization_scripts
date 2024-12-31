#!/bin/bash

repo=$1
url=$2
work_dir="./data/repos"

mkdir -p "${work_dir}" && cd "${work_dir}" || exit

if [ -d "$repo" ]; then
  cd "$repo" || exit
  git pull
  cd ..
else
  git clone "$url"
fi

#!/bin/bash

repo=$1

cd "./data/${repo}" || exit

git add .

sleep 3

git commit -m "update OWNERS"

sleep 1

git push

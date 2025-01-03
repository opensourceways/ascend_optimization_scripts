#!/bin/bash

repo=$1

cd "./data/repos/${repo}" || exit

git add .

sleep 1

git config --global user.name "$GITUSER"

sleep 1

git config --global user.email "$GITEMAIL"

sleep 1

git commit -m "update OWNERS"

sleep 1

git push

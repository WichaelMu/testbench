#1/bin/zsh

set -e

alias py="python3"

py ~/Documents/testbench/excel/descdiff/descdiff.py $1
git diff --word-diff=color --word-diff-regex=. --no-index *.descdiff | colordiff | diff-highlight
rm *.descdiff

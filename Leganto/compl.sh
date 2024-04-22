#!/usr/bin/zsh
set -e

BinaryFile=leganto

mcs -out:$BinaryFile -optimize+ rand.cs && sudo cp $BinaryFile $BINARIES/$BinaryFile

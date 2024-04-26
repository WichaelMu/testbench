#!/usr/bin/zsh
set -e

BinaryFile=leganto
BinaryPath=~/Documents/testbench/Leganto/$BinaryFile
SourceFile=~/Documents/testbench/Leganto/rand.cs

if [ -z "$1" ]
then
	PreprocessorDirectives=""
else
	PreprocessorDirectives=-define:$1
fi

mcs -out:$BinaryPath $PreprocessorDirectives -optimize+ $SourceFile && sudo cp $BinaryPath $BINARIES/$BinaryFile

#!/bin/zsh

if [ -z $1 ]
then
	echo "Please specify a file to templatify."
else
	sed -E -i.bak \
		-e 's|arn:aws:events:.*connection.*"|${leganto_connection_arn}"|g' \
		-e 's|arn:aws:lambda:.*4xx.*"|${leganto_4xx_responder_arn}"|g' \
		-e 's|arn:aws:lambda:.*citations.*"|${leganto_citations_poster_arn}"|g' \
		"$1"
fi


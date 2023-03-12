#!/bin/bash

echo "Hello, World from Pulumi!" > index.html
nohup python -m SimpleHTTPServer 80 &

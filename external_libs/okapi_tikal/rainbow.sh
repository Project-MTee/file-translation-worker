#!/bin/bash
export SWT_GTK3=0
export LIBOVERLAY_SCROLLBAR=0
java -cp "`dirname $0`/lib/*" net.sf.okapi.applications.rainbow.Main "$@"

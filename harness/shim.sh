#!/bin/sh
# Stands where the application looks for wkhtmltopdf (/usr/local/bin/wkhtmltopdf, first on PATH) and
# passes every call to the program under test, /opt/wk/wkhtmltopdf, unchanged: same arguments, same
# exit status, same output. For a conversion it also keeps, in a folder of its own under $WK_LOG, the
# command line, the HTML files it was given, the exit status, the start and end times, what the
# program wrote to stderr, and the PDF, so the report can show what each program was asked to do and
# how long it took.
REAL=/opt/wk/wkhtmltopdf
case "${1:-}" in
--version | -V | -h | --help | -H | --extended-help | --readme | --license) exec "$REAL" "$@" ;;
esac
L=${WK_LOG:-/tmp/wk-calls}
d="$L/$(date +%s%N)-$$"
mkdir -p "$d" 2> /dev/null || exec "$REAL" "$@"
for a in "$@"; do printf '%s\n' "$a"; done > "$d/args.txt"
for a in "$@"; do
    case "$a" in
    *.html) [ -f "$a" ] && cp "$a" "$d/" 2> /dev/null ;;
    esac
done
for a in "$@"; do prev=${last:-}; last=$a; done
# a page given on standard input (pdfkit's "-"), kept too, then given to the program as it came
if [ "$prev" = - ]; then
    cat > "$d/stdin.html"
    s=$(date +%s.%N)
    "$REAL" "$@" < "$d/stdin.html" 2> "$d/stderr.txt"
else
    s=$(date +%s.%N)
    "$REAL" "$@" 2> "$d/stderr.txt"
fi
rc=$?
e=$(date +%s.%N)
[ -f "$last" ] && cp "$last" "$d/out.pdf" 2> /dev/null
# the application may write its files for itself alone: the copies are for anyone to read
chmod -R a+rX "$d" 2> /dev/null
printf '%s %s %s\n' "$rc" "$s" "$e" > "$d/rc.txt"
cat "$d/stderr.txt" >&2
exit $rc

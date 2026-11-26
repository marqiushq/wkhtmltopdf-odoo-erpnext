#!/bin/sh
# Installs, from this system's own repositories, what a Debian package depends on, without installing
# the package itself: for each dependency, the first alternative this system has. A package the
# system has replaced is installed under its new name (python3-pypdf2 became python3-pypdf in
# Debian 13). Prints what it put in another's place and what it could not find.
#
#   sh debian-deps.sh PACKAGE.deb
#   sh debian-deps.sh DEPENDS      (a file holding the package's Depends line alone)
set -eu
deb=$1
case $deb in
*.deb) depends=$(dpkg-deb -f "$deb" Depends) what="$(dpkg-deb -f "$deb" Package) $(dpkg-deb -f "$deb" Version)" ;;
*) depends=$(cat "$deb") what="the package" ;;
esac
apt-get update -q > /dev/null
have() { apt-cache show "$1" > /dev/null 2>&1; }
successor() {
    case $1 in
    python3-pypdf2) echo python3-pypdf ;;
    esac
}
want=""
notes=""
for item in $(echo "$depends" | sed 's/([^)]*)//g; s/:any//g; s/ //g' | tr ',' '\n'); do
    chosen=""
    for alt in $(echo "$item" | tr '|' ' '); do
        if have "$alt"; then
            chosen=$alt
            break
        fi
        new=$(successor "$alt")
        if [ -n "$new" ] && have "$new"; then
            chosen=$new
            notes="$notes $alt (installed as $new)"
            break
        fi
    done
    if [ -n "$chosen" ]; then want="$want $chosen"; else notes="$notes $item (not on this system)"; fi
done
# shellcheck disable=SC2086
apt-get install -y -q --no-install-recommends $want > /tmp/apt.log 2>&1 || {
    tail -40 /tmp/apt.log
    exit 1
}
rm -rf /var/lib/apt/lists/* /tmp/apt.log
echo "dependencies of $what: installed; changed or missing:${notes:- none}"

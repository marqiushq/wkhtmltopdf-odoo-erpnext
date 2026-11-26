#!/usr/bin/env bash
# One ERPNext cell: one ERPNext version on one kind of machine. Each program prints the same documents
# through Frappe's own PDF route, in ERPNext's own Docker image (frappe/erpnext, as frappe_docker
# publishes it: Debian 12 for version 15, Debian 13 for version 16). Its wkhtmltopdf is upstream's
# 0.12.6.1-3 package for Debian 12 (patched Qt), the reference; for marqius-wkhtmltopdf that package
# is removed and the program installed its own way.
#
# The site is made once, as frappe_docker's quick start makes it, with the documents of seed.py; then
# the backend, where Frappe runs wkhtmltopdf, is started with each side's image in turn, on the same
# site and database. A stand-in at /usr/local/bin/wkhtmltopdf (../shim.sh) passes every call to the
# program unchanged and keeps the command line, the exit status and the time taken.
#
#   bash harness/erpnext/cell.sh SERIES ARCH PROGRAMS_DIR OUT_DIR
#
# SERIES: v15 or v16. ARCH: x86-64 or arm64 (the machine's own). PROGRAMS_DIR: what
# harness/programs.sh downloaded and checked. OUT_DIR gets a folder per side, compare-SIDE/ and
# cell.json. PROGRAMS (space-separated) narrows a run by hand; ERP_PORT is the frontend's port (8080).
set -euo pipefail
v=$1 arch=$2
progs=$(cd "$3" && pwd)
mkdir -p "$4"
out=$(cd "$4" && pwd)
here=$(cd "$(dirname "$0")" && pwd)
harness=$(cd "$here/.." && pwd)
root=$(cd "$harness/.." && pwd)
case $arch in
x86-64) plat=linux/amd64 darch=amd64 ;;
arm64) plat=linux/arm64 darch=arm64 ;;
*) echo "::error::unknown machine $arch" >&2; exit 2 ;;
esac
programs=${PROGRAMS:-wkhtmltopdf marqius}
export ERP_PORT=${ERP_PORT:-8080}
P=wkt-erp${v#v} # this cell's compose project and images
work=$(mktemp -d)
export DOCKER_BUILDKIT=1
started=$(date -u +%Y-%m-%dT%H:%M:%SZ)

log() { printf '%s  %s\n' "$(date -u +%H:%M:%S)" "$*"; }
fail() { echo "::error::$*" >&2; exit 1; }
pf() { jq -r --arg p "$1" --arg a "$arch" --arg k "$2" '.files[] | select(.program == $p and .arch == $a) | .[$k]' "$progs/programs.json"; }
sha() { sha256sum "$1" | cut -c1-64; }
compose() { docker compose -p "$P" -f "$here/compose.yml" ${override:+-f "$override"} "$@"; }
cleanup() {
    if [ -n "${sides_pid:-}" ]; then kill "$sides_pid" > /dev/null 2>&1 || true; fi
    override="" BACKEND_IMAGE=${BACKEND_IMAGE:-none} ERP_IMAGE=${ERP_IMAGE:-none} compose down -v --remove-orphans > /dev/null 2>&1 || true
    if [ "${KEEP_IMAGES:-}" != 1 ]; then
        for i in $(docker images -q --filter "reference=$P/*"); do docker rmi -f "$i" > /dev/null 2>&1 || true; done
    fi
    rm -rf "$work"
}
trap cleanup EXIT
cleanup
work=$(mktemp -d)
pull() {
    local t
    for t in 1 2 3; do
        docker pull -q --platform "$plat" "$1" > /dev/null && return 0
        sleep $((t * 15))
    done
    fail "could not pull $1"
}
build() { # NAME FOLDER
    log "building $1"
    docker build --platform "$plat" -t "$P/$1:local" "$2" > "$out/build-$1.log" 2>&1 || {
        tail -40 "$out/build-$1.log"
        fail "the $1 image did not build"
    }
}
mq=$(pf marqius version)
chmod 777 "$out"

# ---- ERPNext's image, and what is in it
log "ERPNext $v on $arch: pulling frappe/erpnext:$v, mariadb:11.8 and redis:6.2-alpine"
pulls=()
for i in "frappe/erpnext:$v" mariadb:11.8 redis:6.2-alpine; do
    (
        trap - EXIT
        pull "$i"
    ) &
    pulls+=($!)
done
for i in "${pulls[@]}"; do wait "$i" || fail "an image could not be pulled"; done
image=$(docker image inspect --format '{{index .RepoDigests 0}}' "frappe/erpnext:$v")
export ERP_IMAGE=$image
system=$(docker run --rm --platform "$plat" --entrypoint sh "$image" -c '. /etc/os-release && echo "$VERSION_CODENAME"')
release=$(docker run --rm --platform "$plat" --entrypoint sh "$image" -c \
    'cd /home/frappe/frappe-bench && env/bin/python -c "import frappe, erpnext; print(\"ERPNext\", erpnext.__version__, \"with Frappe\", frappe.__version__)"')
log "ERPNext's image is $image: $release, on Debian $system"

# the reference must be exactly upstream's package: the program in ERPNext's image is compared, byte
# for byte, with the one inside the package frappe_docker installs (its SHA-256 is pinned in apps.json)
deb=wkhtmltox_0.12.6.1-3.bookworm_$darch.deb
want_deb=$(jq -r --arg a "$arch" '.apps.erpnext.wkhtmltopdf_package[$a]' "$root/apps.json")
curl -fsSL --retry 5 --retry-all-errors -o "$work/$deb" "https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/$deb" ||
    fail "$deb could not be downloaded"
[ "$(sha "$work/$deb")" = "$want_deb" ] || fail "$deb is $(sha "$work/$deb"), not the pinned $want_deb"
want=$(docker run --rm --platform "$plat" -v "$work:/p:ro" debian:trixie sh -c "dpkg-deb -x '/p/$deb' /tmp/x && sha256sum /tmp/x/usr/local/bin/wkhtmltopdf" | cut -c1-64)
got=$(docker run --rm --platform "$plat" --entrypoint sha256sum "$image" /usr/local/bin/wkhtmltopdf | cut -c1-64)
[ "$want" = "$got" ] || fail "the wkhtmltopdf in ERPNext's image is $got, not the $want inside $deb"
log "the wkhtmltopdf in ERPNext's image is the one in $deb ($got)"

# ---- the images, one per side: ERPNext's image with the program at /opt/wk/wkhtmltopdf and the
# stand-in at /usr/local/bin/wkhtmltopdf, where the package puts wkhtmltopdf and pdfkit finds it.
# They build while the site is made (below), and each is checked before it prints.
sides=()
for p in $programs; do sides+=("$system-$p"); done
side_images() {
    local p side d e g
    for p in $programs; do
        side=$system-$p
        d=$work/$side
        mkdir -p "$d"
        cp "$harness/shim.sh" "$d/"
        {
            echo "FROM $image"
            echo 'USER root'
            case $p in
            wkhtmltopdf)
                echo 'RUN mkdir -p /opt/wk && mv /usr/local/bin/wkhtmltopdf /usr/local/bin/wkhtmltoimage /opt/wk/' ;;
            marqius)
                cp -R "$progs/marqius" "$d/mq"
                cp "$progs/marqius-wkhtmltopdf.sh" "$d/mq/"
                echo 'COPY mq /tmp/mq'
                echo "RUN dpkg -r wkhtmltox > /dev/null && MARQIUS_DOWNLOAD=file:///tmp/mq bash /tmp/mq/marqius-wkhtmltopdf.sh --version $mq --prefix /opt/wk && rm -rf /tmp/mq" ;;
            esac
            echo 'COPY shim.sh /usr/local/bin/wkhtmltopdf'
            echo 'RUN chmod 755 /usr/local/bin/wkhtmltopdf'
            echo 'USER frappe'
        } > "$d/Dockerfile"
        build "$side" "$d"
        case $p in
        wkhtmltopdf) e=$want ;;
        marqius) e=$(pf marqius sha256) ;;
        esac
        g=$(docker run --rm --platform "$plat" --entrypoint sh "$P/$side:local" -c 'sha256sum "$(readlink -f /opt/wk/wkhtmltopdf)"' | cut -c1-64)
        [ "$g" = "$e" ] || fail "$side runs a program with SHA-256 $g, not the checked $e"
    done
    log "every side runs the checked program: ${sides[*]}"
}
(
    trap - EXIT
    side_images
) &
sides_pid=$!

# ---- the site, as frappe_docker's quick start makes it, and the documents
override=""
export BACKEND_IMAGE=$image
log "making the site: frappe_docker's quick start, with ERPNext installed"
t0=$(date +%s)
compose up -d --quiet-pull > "$out/compose-up.log" 2>&1 || { tail -30 "$out/compose-up.log"; fail "the site's containers did not start"; }
compose wait create-site > /dev/null 2>&1 || { compose logs create-site | tail -40; fail "the site was not made"; }
compose logs create-site > "$out/create-site.log" 2>&1 || true
# wkhtmltopdf, in the backend, fetches the print stylesheet from the frontend under this name
compose exec -T backend bench --site frontend set-config host_name "http://frontend:8080" > /dev/null
compose cp "$here/seed.py" backend:/home/frappe/frappe-bench/apps/erpnext/erpnext/wkt_seed.py > /dev/null
compose exec -T backend bench --site frontend execute erpnext.wkt_seed.run > "$out/seed.log" 2>&1 || { tail -40 "$out/seed.log"; fail "the documents could not be made"; }
grep -o 'WKT-SEED.*' "$out/seed.log" | sed 's/^WKT-SEED //' > "$out/setup.json.seed" || true
jq -n --slurpfile c "$here/cases.json" --slurpfile s "$out/setup.json.seed" \
    '{cases: [$c[0].cases[] | {name, report: .doctype, names}], notes: $s}' > "$out/setup.json"
log "site and documents made in $(($(date +%s) - t0)) s: $(cat "$out/setup.json.seed")"

# ---- each side prints every case: the backend started with its image, on the same site
wait "$sides_pid" || fail "the sides' images did not build"
sides_pid=""
for side in "${sides[@]}"; do
    log "printing with $side"
    o=$out/$side
    mkdir -p "$o/calls" "$o/pdf"
    chmod -R 777 "$o"
    override=$work/override-$side.yml
    {
        echo 'services:'
        echo '  backend:'
        echo '    volumes:'
        echo "      - \"$out:/results\""
        echo '    environment:'
        echo "      WK_LOG: /results/$side/calls"
    } > "$override"
    export BACKEND_IMAGE=$P/$side:local
    compose up -d --no-deps --force-recreate backend > /dev/null 2>&1 || fail "the backend did not start with $side"
    # nginx keeps the address the backend had when it started: it starts again to find the new one
    compose restart frontend > /dev/null 2>&1 || fail "the frontend did not start again"
    compose exec -T backend sh -c 'wkhtmltopdf --version; echo "exit status $?"' > "$o/version.txt" 2>&1 || true
    compose exec -T backend bench --site frontend clear-cache > /dev/null 2>&1 || true
    python3 "$here/print_cases.py" "http://127.0.0.1:$ERP_PORT" "$o/pdf" "$here/cases.json" || log "$side: the print script ended with an error"
    mv "$o/pdf/prints.json" "$o/prints.json" 2> /dev/null || true
    compose logs backend > "$o/backend.log" 2>&1 || true
done

# ---- the judge (../judge.sh)
ref=$system-wkhtmltopdf
jq -n --arg app erpnext --arg series "$v" --arg release "$release" --arg image "$image" --arg arch "$arch" --arg started "$started" \
    --arg ended "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --arg ref "$ref" \
    --argjson sides "$(printf '%s\n' "${sides[@]}" | jq -R . | jq -s .)" \
    '{app:$app, series:$series, release:$release, image:$image, arch:$arch, started:$started, ended:$ended, reference:$ref,
      sides:$sides}' > "$out/run.json"
bash "$harness/judge.sh" "$out" "$progs" "$arch" "$P"
log "done"

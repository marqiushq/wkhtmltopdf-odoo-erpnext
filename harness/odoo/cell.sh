#!/usr/bin/env bash
# One Odoo cell: one Odoo series on one kind of machine. Each program prints the same documents
# through Odoo's own Print route, on each system it installs on:
#
#   Odoo's image   Odoo's own Docker image (Ubuntu 24.04), as Odoo publishes it: its wkhtmltopdf is
#                  upstream's 0.12.6.1-3 package (patched Qt), the reference. For marqius-wkhtmltopdf
#                  that package is removed and the program installed its own way.
#   Debian 13      Odoo's own Debian package, the very build in the image (checked file by file),
#                  installed with apt, its dependencies from Debian 13. Debian 13 has no wkhtmltopdf.
#
# One database is made with Odoo's demo data and the documents (setup_data.py), then copied for each
# side, so every side prints the same records and nothing one side saves changes what another prints.
# A stand-in at /usr/local/bin/wkhtmltopdf (../shim.sh) passes every call to the program unchanged and
# keeps what Odoo asked for, the exit status and the time taken.
#
#   bash harness/odoo/cell.sh SERIES ARCH PROGRAMS_DIR OUT_DIR
#
# SERIES: 18.0, 19.0 or 20.0. ARCH: x86-64 or arm64 (the machine's own). PROGRAMS_DIR: what
# harness/programs.sh downloaded and checked. OUT_DIR gets a folder per side (the PDFs, Odoo's
# answers, the calls), compare-SIDE/ (marqius-wkhtmltopdf compare against the reference) and
# cell.json (harness/summarise.py). PROGRAMS and SYSTEMS (space-separated) narrow a run by hand.
set -euo pipefail
v=$1 arch=$2
progs=$(cd "$3" && pwd)
mkdir -p "$4"
out=$(cd "$4" && pwd)
here=$(cd "$(dirname "$0")" && pwd)
harness=$(cd "$here/.." && pwd)
case $arch in
x86-64) plat=linux/amd64 ;;
arm64) plat=linux/arm64 ;;
*) echo "::error::unknown machine $arch" >&2; exit 2 ;;
esac
programs=${PROGRAMS:-wkhtmltopdf marqius}
systems=${SYSTEMS:-ubuntu24 debian13}
series_major=${v%%.*}
P=wkt-odoo$series_major # this cell's containers, network, volume and images
net=$P-net vol=$P-data pg=$P-pg
work=$(mktemp -d)
export DOCKER_BUILDKIT=1
started=$(date -u +%Y-%m-%dT%H:%M:%SZ)

log() { printf '%s  %s\n' "$(date -u +%H:%M:%S)" "$*"; }
fail() { echo "::error::$*" >&2; exit 1; }
pf() { jq -r --arg p "$1" --arg a "$arch" --arg k "$2" '.files[] | select(.program == $p and .arch == $a) | .[$k]' "$progs/programs.json"; }
cleanup() {
    for c in $(docker ps -aq --filter "name=^$P-"); do docker rm -f "$c" > /dev/null 2>&1 || true; done
    docker network rm "$net" > /dev/null 2>&1 || true
    docker volume rm "$vol" > /dev/null 2>&1 || true
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
build() { # NAME FOLDER: an image of this cell, from FOLDER/Dockerfile
    log "building $1"
    # On GitHub, an image built only from public ones (CACHED_IMAGES) keeps its layers in GitHub's
    # cache between runs (scope CELL_CACHE-NAME), with the "cells" builder the workflow makes: it then
    # builds in seconds when Odoo's package and debian-deps.sh are unchanged. Elsewhere: docker build.
    local how=(docker build)
    case " ${CACHED_IMAGES:-} " in
    *" $1 "*)
        if [ -n "${CELL_CACHE:-}" ] && docker buildx inspect cells > /dev/null 2>&1; then
            how=(docker buildx build --builder cells --load
                --cache-from "type=gha,scope=$CELL_CACHE-$1"
                --cache-to "type=gha,mode=max,scope=$CELL_CACHE-$1,ignore-error=true")
        fi ;;
    esac
    "${how[@]}" --platform "$plat" -t "$P/$1:local" "$2" > "$out/build-$1.log" 2>&1 || {
        tail -40 "$out/build-$1.log"
        fail "the $1 image did not build"
    }
}

mq=$(pf marqius version)
mkdir -p "$out"
chmod 777 "$out"

# ---- Odoo's image, and what is in it
log "Odoo $v on $arch: pulling odoo:$v, postgres:17 and debian:trixie"
pull "odoo:$v"
pull postgres:17
pull debian:trixie
image=$(docker image inspect --format '{{index .RepoDigests 0}}' "odoo:$v")
release=$(docker run --rm --platform "$plat" --entrypoint dpkg-query "$image" -W -f '${Version}' odoo)
uid=$(docker run --rm --platform "$plat" --entrypoint id "$image" -u odoo)
gid=$(docker run --rm --platform "$plat" --entrypoint id "$image" -g odoo)
log "Odoo's image is $image: Odoo $release, user odoo $uid:$gid"

# the reference must be exactly upstream's package that programs.sh checked: the program in Odoo's
# image is compared, byte for byte, with the one inside that package
deb=$(pf wkhtmltopdf file)
want=$(docker run --rm --platform "$plat" -v "$progs:/p:ro" debian:trixie sh -c "dpkg-deb -x '/p/$deb' /tmp/x && sha256sum /tmp/x/usr/local/bin/wkhtmltopdf" | cut -c1-64)
got=$(docker run --rm --platform "$plat" --entrypoint sha256sum "$image" /usr/local/bin/wkhtmltopdf | cut -c1-64)
[ "$want" = "$got" ] || fail "the wkhtmltopdf in Odoo's image is $got, not the $want inside $deb"
log "the wkhtmltopdf in Odoo's image is the one in $deb ($got)"

# ---- the images, one per side
folder() { rm -rf "${work:?}/$1" && mkdir -p "$work/$1" && cp "$harness/shim.sh" "$work/$1/" && echo "$work/$1"; }
shim='COPY shim.sh /usr/local/bin/wkhtmltopdf
RUN chmod 755 /usr/local/bin/wkhtmltopdf'
install_lines() { # PROGRAM FOLDER: Dockerfile lines that put PROGRAM at /opt/wk/wkhtmltopdf, its own way
    case $1 in
    wkhtmltopdf) # as Odoo's image installs it, moved aside for the stand-in
        echo 'RUN mkdir -p /opt/wk && mv /usr/local/bin/wkhtmltopdf /usr/local/bin/wkhtmltoimage /opt/wk/' ;;
    marqius) # its one-line installer, given the version, reading a copy of marqius.com's files
        cp -R "$progs/marqius" "$2/mq"
        cp "$progs/marqius-wkhtmltopdf.sh" "$2/mq/"
        echo 'COPY mq /tmp/mq'
        echo "RUN (dpkg -r wkhtmltox > /dev/null 2>&1 || true) && MARQIUS_DOWNLOAD=file:///tmp/mq bash /tmp/mq/marqius-wkhtmltopdf.sh --version $mq --prefix /opt/wk && rm -rf /tmp/mq" ;;
    esac
}
sides=()
for s in $systems; do
    if [ "$s" = debian13 ]; then
        d=$(folder debian13-base)
        # Odoo's own Debian package, the very build inside Odoo's image: Odoo keeps every nightly
        # package on its server (its apt index lists only the newest). It must hold exactly the files
        # the image's copy installed: the package's list of files and checksums is compared with the
        # one dpkg kept in the image.
        odoo_deb=odoo_${release}_all.deb
        curl -fsSL --retry 5 --retry-all-errors -o "$d/odoo.deb" "https://nightly.odoo.com/$v/nightly/deb/$odoo_deb" ||
            fail "$odoo_deb could not be downloaded from nightly.odoo.com"
        a=$(docker run --rm --platform "$plat" -v "$d:/w:ro" debian:trixie sh -c 'dpkg-deb -e /w/odoo.deb /tmp/c && sha256sum < /tmp/c/md5sums' | cut -c1-64)
        b=$(docker run --rm --platform "$plat" --entrypoint sh "$image" -c 'sha256sum < /var/lib/dpkg/info/odoo.md5sums' | cut -c1-64)
        [ -n "$a" ] && [ "$a" = "$b" ] || fail "$odoo_deb does not hold the files Odoo's image installed ($a, $b)"
        log "$odoo_deb holds the same files as the Odoo in Odoo's image"
        cp "$harness/debian-deps.sh" "$d/"
        cat > "$d/Dockerfile" << EOF
# Debian 13 with Odoo's own Debian package, the build in Odoo's image. As published it does not
# install on Debian 13: it needs python3-pypdf2, which Debian 13 replaced with python3-pypdf (which
# Odoo also reads). So its dependencies come from Debian 13, python3-pypdf in python3-pypdf2's place
# (debian-deps.sh), and its files are unpacked where the package puts them. No PostgreSQL server: the
# database runs in its own container. User odoo has the same id as in Odoo's image, so both can use
# one data volume.
FROM debian:trixie
ENV DEBIAN_FRONTEND=noninteractive LANG=C.UTF-8
RUN groupadd --system --gid $gid odoo && useradd --system --uid $uid --gid odoo --home-dir /var/lib/odoo --shell /usr/sbin/nologin odoo
COPY odoo.deb debian-deps.sh /tmp/
RUN sh /tmp/debian-deps.sh /tmp/odoo.deb | tee /odoo-dependencies.txt && dpkg-deb -x /tmp/odoo.deb / \\
 && rm -f /tmp/odoo.deb /tmp/debian-deps.sh && mkdir -p /var/lib/odoo && chown odoo:odoo /var/lib/odoo
EOF
        build debian13-base "$d"
    fi
    for p in $programs; do
        [ "$s" = debian13 ] && [ "$p" = wkhtmltopdf ] && continue # Debian 13 has none to install
        side=$s-$p
        d=$(folder "$side")
        {
            if [ "$s" = ubuntu24 ]; then echo "FROM $image"; else echo "FROM $P/debian13-base:local"; fi
            echo 'USER root'
            install_lines "$p" "$d"
            echo "$shim"
            echo 'USER odoo'
        } > "$d/Dockerfile"
        build "$side" "$d"
        sides+=("$side")
    done
done
[ ${#sides[@]} -gt 0 ] || fail "no side to print with"

# every side's program must be the bytes programs.sh checked
expect() { # PROGRAM: the SHA-256 the program at /opt/wk/wkhtmltopdf must have
    case $1 in
    wkhtmltopdf) echo "$want" ;;
    marqius) pf marqius sha256 ;;
    esac
}
for side in "${sides[@]}"; do
    p=${side#*-}
    got=$(docker run --rm --platform "$plat" --entrypoint sh "$P/$side:local" -c 'sha256sum "$(readlink -f /opt/wk/wkhtmltopdf)"' | cut -c1-64)
    e=$(expect "$p")
    [ "$got" = "$e" ] || fail "$side runs a program with SHA-256 $got, not the checked $e"
done
log "every side runs the checked program: ${sides[*]}"

# ---- the database
docker network create "$net" > /dev/null
docker volume create "$vol" > /dev/null
docker run -d --name "$pg" --network "$net" -e POSTGRES_USER=odoo -e POSTGRES_PASSWORD=odoo -e POSTGRES_DB=postgres postgres:17 > /dev/null
for _ in $(seq 90); do docker exec "$pg" pg_isready -U odoo -q 2> /dev/null && break; sleep 2; done
docker exec "$pg" pg_isready -U odoo -q || fail "PostgreSQL did not start"
docker run --rm -v "$vol:/data" debian:trixie chown "$uid:$gid" /data
opts() { echo "--db_host=$pg --db_user=odoo --db_password=odoo --data-dir=/data -d $1"; }
case $series_major in 18) demo="" ;; *) demo="--with-demo" ;; esac # 18 loads demo data unless told not to
log "making the database: account, sale_management and stock, with demo data"
t0=$(date +%s)
# shellcheck disable=SC2046
docker run --rm --network "$net" -v "$vol:/data" --entrypoint odoo "$image" $(opts base) -i account,sale_management,stock $demo \
    --stop-after-init --log-level=warn > "$out/init.log" 2>&1 || { tail -40 "$out/init.log"; fail "Odoo could not make the database"; }
# shellcheck disable=SC2046
docker run --rm -i --network "$net" -v "$vol:/data" -v "$out:/results" -e SETUP_OUT=/results/setup.json --entrypoint odoo "$image" \
    shell $(opts base) --no-http --log-level=warn < "$here/setup_data.py" > "$out/setup.log" 2>&1 || { tail -40 "$out/setup.log"; fail "the documents could not be made"; }
[ -s "$out/setup.json" ] || { tail -40 "$out/setup.log"; fail "no setup.json"; }
log "database and documents made in $(($(date +%s) - t0)) s: $(jq -r '.cases | length' "$out/setup.json") cases"

# ---- each side prints every case
print_side() { # SIDE
    local side=$1 db=s_${1//-/_} c=$P-$1 o=$out/$1 rc=0
    docker exec "$pg" dropdb -U odoo --if-exists "$db"
    docker exec "$pg" createdb -U odoo -T base "$db"
    docker run --rm -v "$vol:/data" debian:trixie sh -c "rm -rf /data/filestore/$db && cp -a /data/filestore/base /data/filestore/$db"
    mkdir -p "$o/calls" "$o/pdf"
    chmod -R 777 "$o"
    # what the program says it is, and what Odoo itself makes of it (the state its Print button acts on)
    docker run --rm --entrypoint sh "$P/$side:local" -c 'wkhtmltopdf --version; echo "exit status $?"' > "$o/version.txt" 2>&1 || true
    # shellcheck disable=SC2046
    docker run --rm -i --network "$net" -v "$vol:/data" --entrypoint odoo "$P/$side:local" shell $(opts "$db") --no-http --log-level=warn \
        < "$here/probe.py" 2>&1 | grep '^ODOO-WKHTML' > "$o/odoo-wkhtml.txt" || true
    # Odoo as in production (2 workers), every case printed through the web client's route
    # shellcheck disable=SC2046
    docker run -d --name "$c" --network "$net" -v "$vol:/data" -v "$out:/results" -v "$here:/w:ro" -e "WK_LOG=/results/$side/calls" \
        --entrypoint odoo "$P/$side:local" $(opts "$db") --db-filter="^$db\$" --workers=2 --max-cron-threads=0 --http-port=8069 \
        --limit-time-real=1200 --limit-time-cpu=900 > /dev/null
    docker exec "$c" python3 /w/print_cases.py http://127.0.0.1:8069 "$db" "/results/$side/pdf" /results/setup.json || rc=$?
    docker logs "$c" > "$o/odoo.log" 2>&1
    docker rm -f "$c" > /dev/null
    mv "$o/pdf/prints.json" "$o/prints.json" 2> /dev/null || true
    return $rc
}
for side in "${sides[@]}"; do
    log "printing with $side"
    print_side "$side" || log "$side: the print script ended with an error"
done

# ---- the judge (../judge.sh): pages, compare against the reference, pictures checked again, cell.json
ref=ubuntu24-wkhtmltopdf
jq -n --arg app odoo --arg series "$v" --arg release "$release" --arg image "$image" --arg arch "$arch" --arg started "$started" \
    --arg ended "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --arg ref "$ref" \
    --argjson sides "$(printf '%s\n' "${sides[@]}" | jq -R . | jq -s .)" \
    '{app:$app, series:$series, release:$release, image:$image, arch:$arch, started:$started, ended:$ended, reference:$ref,
      sides:$sides}' > "$out/run.json"
bash "$harness/judge.sh" "$out" "$progs" "$arch" "$P"
log "done"

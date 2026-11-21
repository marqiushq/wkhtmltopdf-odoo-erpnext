#!/usr/bin/env bash
# The judge, the same for every application: counts each PDF's pages, compares every side's PDFs with
# the reference side's (marqius-wkhtmltopdf compare, the version under test), checks again pixel by
# pixel every picture compare calls changed (pictures.py), and writes cell.json (summarise.py).
#
#   bash harness/judge.sh OUT_DIR PROGRAMS_DIR ARCH IMAGE_PREFIX
#
# OUT_DIR holds run.json (the sides, the reference) and a folder per side with its PDFs in pdf/.
set -euo pipefail
out=$(cd "$1" && pwd)
progs=$(cd "$2" && pwd)
arch=$3 P=$4
harness=$(cd "$(dirname "$0")" && pwd)
case $arch in x86-64) plat=linux/amd64 ;; arm64) plat=linux/arm64 ;; *) echo "::error::unknown machine $arch" >&2; exit 2 ;; esac
log() { printf '%s  %s\n' "$(date -u +%H:%M:%S)" "$*"; }
pf() { jq -r --arg p "$1" --arg a "$arch" --arg k "$2" '.files[] | select(.program == $p and .arch == $a) | .[$k]' "$progs/programs.json"; }

d=$(mktemp -d)
trap 'rm -rf "$d"' EXIT
cp "$progs/marqius/$(pf marqius version)/$(pf marqius file)" "$d/marqius-wkhtmltopdf"
cp "$harness/pictures.py" "$d/"
cat > "$d/Dockerfile" << 'EOF'
FROM debian:trixie
RUN apt-get update -q && apt-get install -y -q --no-install-recommends poppler-utils python3-pil && rm -rf /var/lib/apt/lists/*
COPY marqius-wkhtmltopdf /usr/local/bin/marqius-wkhtmltopdf
COPY pictures.py /usr/local/bin/pictures.py
RUN chmod 755 /usr/local/bin/marqius-wkhtmltopdf
EOF
log "building the judge"
docker build --platform "$plat" -t "$P/judge:local" "$d" > "$out/build-judge.log" 2>&1 || { tail -30 "$out/build-judge.log"; exit 1; }

# what the containers wrote, readable by anyone (the report and the run's artifacts read it)
docker run --rm -v "$out:/results" debian:trixie chmod -R a+rX /results
ref=$(jq -r .reference "$out/run.json")
docker run --rm -v "$out:/results" "$P/judge:local" sh -c '
    for d in /results/*/pdf; do
        for f in "$d"/*.pdf; do [ -f "$f" ] && printf "%s\t%s\n" "$(basename "$f" .pdf)" "$(pdfinfo "$f" 2> /dev/null | sed -n "s/^Pages: *//p")"; done > "${d%/pdf}/pages.tsv"
    done'
if [ -d "$out/$ref/pdf" ]; then
    for side in $(jq -r '.sides[]' "$out/run.json"); do
        [ "$side" = "$ref" ] && continue
        log "compare: $ref against $side"
        docker run --rm -v "$out:/results" "$P/judge:local" marqius-wkhtmltopdf compare "/results/$ref/pdf" "/results/$side/pdf" \
            -o "/results/compare-$side" > "$out/compare-$side.txt" 2>&1 || true
        grep -E '^(GO|REVIEW|NO-GO)' "$out/compare-$side.txt" | sed 's/^/    compare: /' || true
        docker run --rm -v "$out:/results" "$P/judge:local" python3 /usr/local/bin/pictures.py "/results/compare-$side" "/results/$ref/pdf" \
            "/results/$side/pdf" 2>&1 | sed 's/^/    /' || true
    done
fi
docker rmi -f "$P/judge:local" > /dev/null 2>&1 || true
python3 "$harness/summarise.py" "$out" "$progs/programs.json"

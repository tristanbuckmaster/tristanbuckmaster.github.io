#!/usr/bin/env bash
set -euo pipefail

# Overlay this build. Courant also serves documents and configuration kept outside Git.
options=(--checksum --itemize-changes --delay-updates --from0 --files-from=- --no-implied-dirs
         --exclude='/statement.pdf' --exclude='.htaccess')
case "$#:${1-}" in
  0:|1:--dry-run) options+=(--dry-run) ;;
  1:--apply) ;;
  *) echo "Usage: $0 [--dry-run | --apply]" >&2; exit 2 ;;
esac

cd -- "$(dirname -- "$0")"
destination=${COURANT_DESTINATION:-tb97@access.cims.nyu.edu:/web/tb97/}
bin/build-cv --check
build_dir=$(mktemp -d)
trap 'rm -rf -- "$build_dir"' EXIT
BUNDLE_FROZEN=true JEKYLL_ENV=production bundle exec jekyll build --destination "$build_dir/site"
test -s "$build_dir/site/index.html"

# Only send files. An existing file where a new directory would be needed must
# cause an error rather than be replaced by rsync's recursive directory update.
(cd "$build_dir/site" && find . -type f -print0) |
  rsync "${options[@]}" -- "$build_dir/site/" "$destination"


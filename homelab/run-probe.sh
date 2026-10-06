#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
command -v docker >/dev/null || { echo 'Brak Dockera na tej VM.'; exit 1; }
command -v curl >/dev/null || { echo 'Zainstaluj curl na VM.'; exit 1; }
command -v git >/dev/null || { echo 'Zainstaluj git na VM.'; exit 1; }
mkdir -p .local/output
chmod 700 .local .local/output
# Use the host user's UID; never run the Chromium process as root.
export TRACKER_UID="${SUDO_UID:-$(id -u)}" TRACKER_GID="${SUDO_GID:-$(id -g)}"
if [ "$TRACKER_UID" = 0 ]; then
  echo 'Uruchom skrypt jako zwykły użytkownik VM, nie z powłoki root.'
  exit 1
fi
if docker info >/dev/null 2>&1; then D=(docker); else D=(sudo docker); fi
"${D[@]}" compose version >/dev/null
# Official Playwright seccomp profile, pinned and verified by Git blob hash.
PROFILE=.local/seccomp_profile.json
if [ ! -f "$PROFILE" ]; then
  curl --fail --location --proto '=https' --tlsv1.2 --max-time 30 \
    https://raw.githubusercontent.com/microsoft/playwright/v1.63.0/utils/docker/seccomp_profile.json \
    --output "$PROFILE.tmp"
  mv "$PROFILE.tmp" "$PROFILE"
fi
if [ "$(git hash-object "$PROFILE")" != fddc05fb520affb145404e6f6f647ca96af8087d ]; then
  echo 'Profil seccomp ma inny hash. Nie uruchamiam kontenera.'
  exit 1
fi
# sudo may filter env; values are passed explicitly as CLI environment to Compose.
CMD=("${D[@]}" compose --project-name insignia-probe -f compose.yaml)
# .env is local-only, not a credential store.
printf 'TRACKER_UID=%s\nTRACKER_GID=%s\n' "$TRACKER_UID" "$TRACKER_GID" > .local/compose.env
CMD=("${D[@]}" compose --env-file .local/compose.env --project-name insignia-probe -f compose.yaml)
"${CMD[@]}" build
"${CMD[@]}" run --rm --entrypoint python probe -m unittest discover -s tests -v
set +e
"${CMD[@]}" run --rm probe "$@"
RESULT=$?
set -e
"${CMD[@]}" down
printf '\nRaport do przekazania: %s/.local/output/report-share.json\n' "$(pwd)"
printf 'Pełne HTML i obrazy: prywatny katalog .local/output — nie wysyłaj go do publicznego repo.\n'
exit "$RESULT"

#!/usr/bin/env bash
set -euo pipefail
repo=$(pwd)
work=${1:?usage: ci/build_slang_pilots.sh NEW_WORK_DIRECTORY}
mkdir "$work"
work=$(cd "$work" && pwd)
mkdir "$work/evidence"
exec > >(tee "$work/evidence/bootstrap.log") 2>&1
set -x
fetch() {
  git init "$work/$1"
  git -C "$work/$1" remote add origin "https://github.com/$2.git"
  git -C "$work/$1" fetch --depth 1 origin "$3"
  git -C "$work/$1" checkout --detach FETCH_HEAD
  test "$(git -C "$work/$1" rev-parse HEAD)" = "$3"
  printf '%s %s\n' "$1" "$3" >> "$work/evidence/source-revisions.txt"
}
fetch slang MikePopoloski/slang e222e7dc0250231312f14c37d47404a49df00fe2
fetch fmt fmtlib/fmt 1be298e1bd68957e4cd352e1f676f00e07dcfb57
fetch boost_regex MikePopoloski/regex 2b3ac0834f31086c6e3c0e0ceb8516e427d5c39d
fetch mimalloc microsoft/mimalloc acf2fdd329f9dc2a7ffe3f12a133fe7175e39378
fetch tomlplusplus marzer/tomlplusplus 30172438cee64926dc41fdd9c11fb3ba5b2ba9de
fetch caliptra chipsalliance/caliptra-rtl 49370266d12cb0c4a8f71b3a0ff7e54ba7d4866e
fetch opentitan lowRISC/opentitan 7a3ad34b6d483f4d1d69ac670ddb1c45f1172e19
uname -a > "$work/evidence/host.txt"
cat /etc/os-release >> "$work/evidence/host.txt"
python3 --version >> "$work/evidence/host.txt"
g++ --version >> "$work/evidence/host.txt"
cmake --version >> "$work/evidence/host.txt"
dpkg-query -W > "$work/evidence/packages.txt"
git rev-parse HEAD > "$work/evidence/qd-lint-revision.txt"
cmake -S "$work/slang" -B "$work/build" -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DSLANG_INCLUDE_TESTS=OFF -DSLANG_INCLUDE_INSTALL=OFF \
  -DFETCHCONTENT_TRY_FIND_PACKAGE_MODE=NEVER \
  -DFETCHCONTENT_SOURCE_DIR_FMT="$work/fmt" \
  -DFETCHCONTENT_SOURCE_DIR_BOOST_REGEX="$work/boost_regex" \
  -DFETCHCONTENT_SOURCE_DIR_MIMALLOC="$work/mimalloc" \
  -DFETCHCONTENT_SOURCE_DIR_TOMLPLUSPLUS="$work/tomlplusplus" \
  > "$work/evidence/configure.log" 2>&1
cmake --build "$work/build" --target slang -j2 > "$work/evidence/build.log" 2>&1
cp "$work/build/CMakeCache.txt" "$work/evidence/"
export PATH="$work/build/bin:$PATH"
slang --version > "$work/evidence/slang-version.txt"
sha256sum "$work/build/bin/slang" > "$work/evidence/slang-binary.sha256"
cd "$repo"
python3 -m unittest -v > "$work/evidence/python-tests.log" 2>&1
/usr/bin/time -v -o "$work/evidence/resource.log" \
  python3 ci/run_slang_pilots.py "$work/caliptra" "$work/opentitan" "$work/evidence/pilot" \
  > "$work/evidence/pilot.log" 2>&1
for source in slang fmt boost_regex mimalloc tomlplusplus caliptra opentitan; do
  git -C "$work/$source" diff --exit-code
  git -C "$work/$source" diff --cached --exit-code
done

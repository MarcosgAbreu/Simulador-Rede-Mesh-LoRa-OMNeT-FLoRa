#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
VERSIONS_FILE="${PROJECT_ROOT}/config/versions.env"

if [[ ! -f "${VERSIONS_FILE}" ]]; then
    printf 'Arquivo de versões não encontrado: %s\n' "${VERSIONS_FILE}" >&2
    exit 1
fi
# shellcheck disable=SC1090
source "${VERSIONS_FILE}"

DOWNLOAD_DIR="${PROJECT_ROOT}/downloads"
THIRD_PARTY_DIR="${PROJECT_ROOT}/third_party"
OMNETPP_ROOT="${THIRD_PARTY_DIR}/omnetpp-${OMNETPP_VERSION}"
INET_ROOT="${THIRD_PARTY_DIR}/inet4.6"
FLORA_ROOT="${THIRD_PARTY_DIR}/flora"

log() {
    printf '[install] %s\n' "$*"
}

die() {
    printf '[install] ERRO: %s\n' "$*" >&2
    exit 1
}

run_step() {
    log "$*"
    "$@"
}

if [[ "$(uname -r)" != *Microsoft* && "$(uname -r)" != *microsoft* && "${FORCE_NATIVE_UBUNTU:-0}" != 1 ]]; then
    die "este script espera WSL2; use FORCE_NATIVE_UBUNTU=1 somente em Ubuntu nativo."
fi

if [[ "${SKIP_APT:-0}" != 1 ]]; then
    if ! command -v sudo >/dev/null 2>&1; then
        die "sudo não está instalado."
    fi
    run_step sudo apt-get update
    run_step sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
        build-essential bison flex perl python3 python3-pip python3-venv python3-tk \
        curl wget git make cmake pkg-config ffmpeg \
        libxml2-dev zlib1g-dev libpcap-dev \
        qtbase5-dev qtchooser qt5-qmake qtbase5-dev-tools libqt5opengl5-dev \
        qt6-base-dev qt6-tools-dev qt6-tools-dev-tools
else
    log "SKIP_APT=1: usando dependências do sistema já instaladas"
fi

if [[ ! -x "${PROJECT_ROOT}/.venv/bin/python" ]]; then
    run_step python3 -m venv "${PROJECT_ROOT}/.venv"
fi
run_step "${PROJECT_ROOT}/.venv/bin/python" -m pip install --upgrade pip
run_step "${PROJECT_ROOT}/.venv/bin/python" -m pip install -r "${PROJECT_ROOT}/requirements-dev.txt"
export PATH="${PROJECT_ROOT}/.venv/bin:${PATH}"

mkdir -p "${DOWNLOAD_DIR}" "${THIRD_PARTY_DIR}"

download() {
    local url="$1"
    local destination="$2"
    if [[ ! -s "${destination}" ]]; then
        run_step curl --fail --location --retry 3 --output "${destination}.part" "${url}"
        mv -- "${destination}.part" "${destination}"
    else
        log "já baixado: ${destination}"
    fi
}

extract() {
    local archive="$1"
    local expected_dir="$2"
    if [[ ! -d "${expected_dir}" ]]; then
        run_step tar --extract --gzip --file "${archive}" --directory "${THIRD_PARTY_DIR}"
    else
        log "já extraído: ${expected_dir}"
    fi
    [[ -d "${expected_dir}" ]] || die "o arquivo ${archive} não criou ${expected_dir}"
}

build_omnetpp() {
    if [[ ! -x "${OMNETPP_ROOT}/bin/opp_run" ]]; then
        pushd "${OMNETPP_ROOT}" >/dev/null
        # OMNeT++ exige que o ambiente seja carregado antes do configure.
        # shellcheck disable=SC1091
        set +u
        source ./setenv -q
        set -u
        run_step ./configure WITH_QTENV=yes WITH_OSG=no
        run_step make -j"$(nproc)"
        popd >/dev/null
    else
        log "OMNeT++ já compilado"
    fi
}

build_framework() {
    local root="$1"
    if [[ "${root}" == "${FLORA_ROOT}" && ! -f "${root}/src/Makefile" ]]; then
        local inet_relative
        inet_relative="$(realpath --relative-to="${root}" "${INET_ROOT}")"
        pushd "${root}" >/dev/null
        run_step make INET_DIR="${inet_relative}" makefiles
        popd >/dev/null
    elif [[ ! -f "${root}/src/Makefile" && ! -f "${root}/Makefile" ]]; then
        die "Makefile não encontrado em ${root}"
    fi
    if ! compgen -G "${root}/out/*/src/lib${2}.so" >/dev/null &&
       [[ ! -f "${root}/src/lib${2}.so" && ! -f "${root}/lib${2}.so" ]]; then
        pushd "${root}" >/dev/null
        run_step make -j"$(nproc)"
        popd >/dev/null
    else
        log "framework já compilado: ${root}"
    fi
}

download "${OMNETPP_URL}" "${DOWNLOAD_DIR}/omnetpp-${OMNETPP_VERSION}.tgz"
download "${INET_URL}" "${DOWNLOAD_DIR}/inet-${INET_VERSION}.tgz"
download "${FLORA_URL}" "${DOWNLOAD_DIR}/flora-${FLORA_VERSION}.tgz"

extract "${DOWNLOAD_DIR}/omnetpp-${OMNETPP_VERSION}.tgz" "${OMNETPP_ROOT}"
extract "${DOWNLOAD_DIR}/inet-${INET_VERSION}.tgz" "${INET_ROOT}"
extract "${DOWNLOAD_DIR}/flora-${FLORA_VERSION}.tgz" "${FLORA_ROOT}"

run_step "${PROJECT_ROOT}/.venv/bin/python" -m pip install -r \
    "${OMNETPP_ROOT}/python/requirements.txt"
build_omnetpp
# shellcheck disable=SC1090
set +u
source "${OMNETPP_ROOT}/setenv" -q
set -u
build_framework "${INET_ROOT}" "INET"
build_framework "${FLORA_ROOT}" "flora"

sed \
    -e "s|@PROJECT_ROOT@|${PROJECT_ROOT}|g" \
    -e "s|@OMNETPP_ROOT@|${OMNETPP_ROOT}|g" \
    -e "s|@INET_ROOT@|${INET_ROOT}|g" \
    -e "s|@FLORA_ROOT@|${FLORA_ROOT}|g" \
    "${SCRIPT_DIR}/env.sh.in" > "${SCRIPT_DIR}/env.sh"
chmod +x "${SCRIPT_DIR}/env.sh"

log "instalação concluída; carregue o ambiente com: source scripts/env.sh"

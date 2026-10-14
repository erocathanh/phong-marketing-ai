#!/usr/bin/env bash
# Install skills and agent links into ~/.claude/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
SKILLS_SRC="${REPO_ROOT}/.claude/skills"
AGENTS_SRC="${REPO_ROOT}/.claude/agents"

TARGET_SKILLS_DIR="${HOME}/.claude/skills"
TARGET_AGENTS_DIR="${HOME}/.claude/agents"

mkdir -p "${TARGET_SKILLS_DIR}"

if [ -d "${SKILLS_SRC}" ]; then
  for skill_path in "${SKILLS_SRC}"/*; do
    [ -d "${skill_path}" ] || continue
    skill_name="$(basename "${skill_path}")"
    dest="${TARGET_SKILLS_DIR}/${skill_name}"

    if [ -L "${dest}" ]; then
      current_target="$(readlink "${dest}")"
      if [ "${current_target}" = "${skill_path}" ]; then
        echo "ĐÃ CÓ: ${skill_name} -> ${skill_path} (bỏ qua)"
        continue
      else
        echo "BỎ QUA (trỏ chỗ khác): ${skill_name} -> ${current_target}"
        continue
      fi
    elif [ -e "${dest}" ]; then
      echo "BỎ QUA (tệp/thư mục thật tồn tại): ${dest}"
      continue
    fi

    ln -s "${skill_path}" "${dest}"
    echo "ĐÃ NỐI: ${skill_name} -> ${skill_path}"
  done
fi

# Chừa sẵn chỗ cho tệp vai ghế trong .claude/agents/
if [ -d "${AGENTS_SRC}" ]; then
  mkdir -p "${TARGET_AGENTS_DIR}"
  for agent_path in "${AGENTS_SRC}"/*; do
    [ -e "${agent_path}" ] || continue
    agent_name="$(basename "${agent_path}")"
    dest="${TARGET_AGENTS_DIR}/${agent_name}"

    if [ -L "${dest}" ]; then
      current_target="$(readlink "${dest}")"
      if [ "${current_target}" = "${agent_path}" ]; then
        echo "ĐÃ CÓ: ${agent_name} -> ${agent_path} (bỏ qua)"
        continue
      else
        echo "BỎ QUA (trỏ chỗ khác): ${agent_name} -> ${current_target}"
        continue
      fi
    elif [ -e "${dest}" ]; then
      echo "BỎ QUA (tệp/thư mục thật tồn tại): ${dest}"
      continue
    fi

    ln -s "${agent_path}" "${dest}"
    echo "ĐÃ NỐI: ${agent_name} -> ${agent_path}"
  done
fi

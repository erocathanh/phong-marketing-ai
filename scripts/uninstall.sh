#!/usr/bin/env bash
# Uninstall symlinks pointing to this repository from ~/.claude/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"

TARGET_SKILLS_DIR="${HOME}/.claude/skills"
TARGET_AGENTS_DIR="${HOME}/.claude/agents"

# Danh sách đúng 7 skill của kho này
ALLOWED_SKILLS=(
  "caption-fanpage"
  "doc-so-quang-cao"
  "lich-dang-7-ngay"
  "fb-chia-khoa"
  "fanpage-post"
  "doc-comment-fanpage"
  "tra-loi-inbox-fanpage"
)

# Danh sách đúng 8 tệp vai của kho này
ALLOWED_AGENTS=(
  "marketing-lead.md"
  "content-writer.md"
  "social-community.md"
  "email-crm.md"
  "paid-media.md"
  "video-creative.md"
  "funnel-offer.md"
  "marketing-reviewer.md"
)

if [ -d "${TARGET_SKILLS_DIR}" ]; then
  for skill in "${ALLOWED_SKILLS[@]}"; do
    dest="${TARGET_SKILLS_DIR}/${skill}"
    if [ -L "${dest}" ]; then
      target="$(readlink "${dest}")"
      if [ "${target}" = "${REPO_ROOT}/.claude/skills/${skill}" ]; then
        rm "${dest}"
        echo "ĐÃ GỠ: ${skill} (từng trỏ tới ${target})"
      fi
    fi
  done
fi

if [ -d "${TARGET_AGENTS_DIR}" ]; then
  for agent in "${ALLOWED_AGENTS[@]}"; do
    dest="${TARGET_AGENTS_DIR}/${agent}"
    if [ -L "${dest}" ]; then
      target="$(readlink "${dest}")"
      if [ "${target}" = "${REPO_ROOT}/.claude/agents/${agent}" ]; then
        rm "${dest}"
        echo "ĐÃ GỠ: ${agent} (từng trỏ tới ${target})"
      fi
    fi
  done
fi

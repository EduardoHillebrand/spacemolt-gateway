#!/bin/bash
# Uso: PROJECT=/path/to/repo bash /tmp/git_step_clean.sh <branch> <mensagem>
set -e
BRANCH="$1"
MESSAGE="$2"
if [ -z "$BRANCH" ] || [ -z "$MESSAGE" ]; then echo "Uso: git_step.sh <branch> <mensagem>"; exit 1; fi
TOKEN=$(tr -d '\r\n' < "$PROJECT/.github_token")
REMOTE="https://${TOKEN}@github.com/EduardoHillebrand/spacemolt-gateway.git"
TMP=/tmp/sgw_git
echo "==> Sincronizando repo..."
if [ -d "$TMP/.git" ]; then
  cd "$TMP" && git remote set-url origin "$REMOTE" && git fetch origin && git checkout main && git reset --hard origin/main
else
  git clone "$REMOTE" "$TMP" && cd "$TMP" && git config user.email "eduardo.hillebrand@gmail.com" && git config user.name "EduardoHillebrand"
fi
echo "==> Copiando arquivos..."
rsync -a --delete --no-perms --chmod=ugo=rw --exclude='.git/' --exclude='.venv/' --exclude='__pycache__/' --exclude='.pytest_cache/' --exclude='*.egg-info/' --exclude='.github_token' "$PROJECT/" "$TMP/"
python3 "$PROJECT/scripts/clean_files.py" "$TMP"
echo "==> Rodando testes..."
bash /tmp/run_tests_clean.sh
echo "==> Commitando em $BRANCH..."
cd "$TMP" && git checkout -b "$BRANCH" && git add -A
if git diff --cached --quiet; then
  echo "Nenhuma mudanca para commitar."
else
  git commit -m "$MESSAGE" && git checkout main && git merge --no-ff "$BRANCH" && git push
  echo "Passo $BRANCH concluido e publicado."
fi

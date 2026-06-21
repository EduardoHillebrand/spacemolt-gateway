#!/bin/bash
# Cria branch, sincroniza arquivos, roda testes, commita, merge na main e push.
# Uso: git_step.sh <branch> <mensagem-de-commit>
# Exemplo: git_step.sh 006_manual-check "docs: manual check and README instructions"

set -e

BRANCH="$1"
MESSAGE="$2"

if [ -z "$BRANCH" ] || [ -z "$MESSAGE" ]; then
  echo "Uso: git_step.sh <branch> <mensagem>"
  exit 1
fi

PROJECT="$(cd "$(dirname "$0")/.." && pwd)"
TOKEN=$(cat "$PROJECT/.github_token" | tr -d '\0\r\n')
REMOTE="https://${TOKEN}@github.com/EduardoHillebrand/spacemolt-gateway.git"
TMP=/tmp/sgw_git

echo "==> Sincronizando repo em $TMP..."
if [ -d "$TMP/.git" ]; then
  cd "$TMP"
  git remote set-url origin "$REMOTE"
  git fetch origin
  git checkout main
  git reset --hard origin/main
else
  git clone "$REMOTE" "$TMP"
  cd "$TMP"
  git config user.email "eduardo.hillebrand@gmail.com"
  git config user.name "EduardoHillebrand"
fi

echo "==> Copiando arquivos do projeto..."
rsync -a --delete \
  --exclude='.git/' \
  --exclude='.venv/' \
  --exclude='__pycache__/' \
  --exclude='.pytest_cache/' \
  --exclude='*.egg-info/' \
  --exclude='.github_token' \
  "$PROJECT/" "$TMP/"

echo "==> Rodando testes..."
bash "$PROJECT/scripts/run_tests.sh"

echo "==> Criando branch $BRANCH..."
cd "$TMP"
git checkout -b "$BRANCH"
git add -A
git commit -m "$MESSAGE"

echo "==> Merge na main e push..."
git checkout main
git merge --no-ff "$BRANCH"
git push

echo ""
echo "✓ Passo $BRANCH concluído e publicado."

#!/bin/bash
# Hook: PostToolUse — valida que los archivos spec tengan frontmatter correcto
# Se ejecuta después de Write/Edit en archivos .spec.md
# Solo advierte (exit 0) — no bloquea.

TOOL_INPUT=$(cat)
FILE_PATH=$(echo "$TOOL_INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('file_path',''))" 2>/dev/null)

# Solo actuar sobre archivos .spec.md
if ! echo "$FILE_PATH" | grep -q "\.spec\.md$"; then
  exit 0
fi

# Verificar que el archivo tiene frontmatter con status
if [ -f "$FILE_PATH" ]; then
  if ! grep -q "^status:" "$FILE_PATH" && ! grep -q "^status: " "$FILE_PATH"; then
    echo "⚠️  AVISO: '$FILE_PATH' no tiene campo 'status:' en el frontmatter." >&2
    echo "   Las specs deben incluir: id, status, feature, created, updated, author, version" >&2
  fi

  # Advertir si el status es DRAFT y se está en una rama feat/
  BRANCH=$(git branch --show-current 2>/dev/null)
  STATUS=$(grep "^status:" "$FILE_PATH" 2>/dev/null | head -1 | awk '{print $2}')
  if [ "$STATUS" = "DRAFT" ] && echo "$BRANCH" | grep -q "^feat/"; then
    echo "⚠️  AVISO: La spec '$FILE_PATH' está en DRAFT." >&2
    echo "   Recuerda aprobarla (status: APPROVED) antes de iniciar implementación." >&2
  fi
fi

exit 0

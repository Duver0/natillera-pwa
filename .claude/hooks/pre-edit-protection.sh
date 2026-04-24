#!/bin/bash
# Hook: PreToolUse — protege archivos sensibles antes de Edit/Write
# Se ejecuta antes de cualquier operación Edit o Write.
# Exit 2 + mensaje en stderr bloquea la operación y comunica la razón a Claude.

TOOL_INPUT=$(cat)
FILE_PATH=$(echo "$TOOL_INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('file_path',''))" 2>/dev/null)

# Archivos que NUNCA deben modificarse directamente
PROTECTED_PATTERNS=(
  "\.env"
  "\.env\."
  "firebase_credentials\.json"
  "secrets/"
  "\.git/"
  "node_modules/"
  "__pycache__/"
  "settings\.local\.json"
)

for pattern in "${PROTECTED_PATTERNS[@]}"; do
  if echo "$FILE_PATH" | grep -qE "$pattern"; then
    echo "BLOCKED: '$FILE_PATH' está en la lista de archivos protegidos." >&2
    echo "Este archivo no debe modificarse directamente. Consulta al usuario si necesitas hacer cambios en configuración sensible." >&2
    exit 2
  fi
done

exit 0

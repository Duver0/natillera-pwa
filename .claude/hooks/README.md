# Hooks de Claude Code

Este directorio contiene los scripts de hooks del proyecto. Los hooks se configuran en `.claude/settings.json`.

## Hooks activos

| Script | Evento | Matcher | Descripción |
|--------|--------|---------|-------------|
| `pre-edit-protection.sh` | `PreToolUse` | `Edit\|Write` | Bloquea edición de archivos sensibles (.env, firebase_credentials, secrets/) |
| `post-spec-validate.sh` | `PostToolUse` | `Write\|Edit` | Valida frontmatter en archivos `.spec.md` tras escribirlos |
| (en settings.json) | `Stop` | — | Notificación de sonido al terminar |
| (en settings.json) | `SubagentStop` | — | Notificación de sonido al terminar subagente |
| (en settings.json) | `Notification` | — | Notificación de sonido en confirmaciones |

## Control de flujo de hooks

| Exit code | Efecto |
|-----------|--------|
| `exit 0` | La operación procede normalmente |
| `exit 2` | La operación es BLOQUEADA — stderr se muestra a Claude como razón |
| `exit 1` | Error del hook — no bloquea la operación |

## Agregar un nuevo hook

1. Crear el script en este directorio (ej. `mi-hook.sh`)
2. Darle permisos de ejecución: `chmod +x .claude/hooks/mi-hook.sh`
3. Registrarlo en `.claude/settings.json`:

```json
"hooks": {
  "PreToolUse": [
    {
      "matcher": "Edit|Write",
      "hooks": [
        {
          "type": "command",
          "command": ".claude/hooks/mi-hook.sh"
        }
      ]
    }
  ]
}
```

## Eventos disponibles

- `PreToolUse` — antes de ejecutar una herramienta (puede bloquear con exit 2)
- `PostToolUse` — después de que una herramienta termina
- `UserPromptSubmit` — cuando el usuario envía un prompt
- `Stop` — cuando Claude termina de responder
- `SubagentStart` / `SubagentStop` — ciclo de vida de subagentes
- `Notification` — cuando Claude necesita atención
- `SessionStart` / `SessionEnd` — ciclo de vida de sesión

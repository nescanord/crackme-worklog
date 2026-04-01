NecrumWin (Reezli challenge) - README operativo
===============================================

Objetivo principal:
- recuperar una password valida

Objetivo secundario:
- construir un bypass estable

Situacion actual
----------------

El proyecto ya no esta centrado en el viejo eje `DEADC0DE -> xabort -> trampolines`.
Ese trabajo sigue documentado, pero la pista de Reezli y la validacion dinamica de la
ruta del titulo han movido el frente principal de nuevo a la password.

Lo confirmado ahora:
- `crackme | reezli.vc` es una ruta real
- `Detected.` sale por el buffer real de `NtWriteFile`
- las strings tipo `auth_login_success` son senuelos
- la ruta temprana tras el titulo pasa por RVAs reales dentro del bloque protegido
- el problema principal actual es instrumentar esa ruta sin disparar deteccion

Scripts canonicos
-----------------

- `scripts/core/runtime_probe.py`
- `scripts/probes/crackme_reezli_main_path_probe.py`
- `scripts/probes/crackme_ntio_path_probe.py`

Fuentes de verdad
-----------------

- `README.md`
- `findings.md`
- `timeline.md`
- `next-steps.md`
- `notes/memoria_canonica.txt`
- `notes/source-clues/2026-04-01-reezli-hint.md`

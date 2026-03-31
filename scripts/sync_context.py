import argparse
import datetime as dt
import subprocess
from pathlib import Path


ROOT = Path(r"C:\Users\nesca\Desktop\NecrumWin-Reezli")
REPO = ROOT / "analysis" / "worklog" / "crackme-worklog"
NOTES_DIR = ROOT / "analysis" / "notes"
REPO_NOTES_DIR = REPO / "notes"


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace").strip()


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(REPO), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return result.stdout.strip()


def build_canonical() -> str:
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log = git("log", "--oneline", "--decorate", "-n", "20")
    readme = read_text(REPO / "README.md")
    findings = read_text(REPO / "findings.md")
    timeline = read_text(REPO / "timeline.md")
    next_steps = read_text(REPO / "next-steps.md")
    legacy = read_text(REPO_NOTES_DIR / "legacy_memory_sources.txt")

    parts = [
        "NecrumWin (Reezli challenge) - memoria canonica sincronizada",
        "===========================================================",
        "",
        f"Generado: {now}",
        "",
        "Fuente canonica",
        "--------------",
        "Este documento se genera desde el worklog real del repo y debe prevalecer sobre memorias manuales antiguas.",
        "",
        "Commits recientes",
        "-----------------",
        log,
        "",
        "README",
        "------",
        readme,
        "",
        "Findings",
        "--------",
        findings,
        "",
        "Timeline",
        "--------",
        timeline,
        "",
        "Next Steps",
        "----------",
        next_steps,
        "",
        "Memorias heredadas desactualizadas",
        "----------------------------------",
        legacy,
    ]
    return "\n".join(parts).strip() + "\n"


def build_summary() -> str:
    log = git("log", "--oneline", "-n", "8")
    next_steps = read_text(REPO / "next-steps.md")

    summary = [
        "NecrumWin (Reezli challenge) - resumen operativo sincronizado",
        "============================================================",
        "",
        "Este resumen corto se deriva de la memoria canonica y del repo.",
        "",
        "Estado actual",
        "-------------",
        "- la fuente de verdad es el repo `crackme-worklog`, no las memorias manuales aisladas",
        "- la linea mas nueva ya no es solo `R10 -> R8 -> ESI`; ahora incluye la rama `family14`, la trampa `xabort` y una cadena de trampolines tardios",
        "- choke points actuales mas utiles:",
        "  - `0x1e0ae4c`",
        "  - `0x1203bb4`",
        "  - `0x5a6c54a`",
        "  - `0x55efa2`",
        "  - `0x5898a23`",
        "  - `0x55da697`",
        "  - `0x446f267`",
        "",
        "Hallazgo mas reciente",
        "---------------------",
        "- la ruta mas avanzada ya no muere en `xabort`; ahora se desenrolla una cadena de trampolines tardios",
        "- parches tardios productivos hasta ahora:",
        "  - `0x1e0ae4c -> ret`",
        "  - `0x1203bb4 -> add rsp, 8 ; ret`",
        "  - `0x5a6c54a -> xor cx, cx ; nop`",
        "  - `0x55efa2 -> ret`",
        "  - `0x5898a23 -> ret`",
        "  - `0x55da697 -> add rsp, 8 ; ret`",
        "- la progresion de fallos observada es:",
        "  - `crackme+0x1e0ae4c`",
        "  - `crackme+0x5a6c54a`",
        "  - `0x800000023`",
        "  - `crackme+0x446f267`",
        "",
        "Implicacion",
        "-----------",
        "- el bypass actual parece una cadena de trampolines, no un unico branch final",
        "- el bypass sigue pareciendo mas cercano que la password exacta",
        "",
        "Commits recientes",
        "-----------------",
        log,
        "",
        "Siguiente paso",
        "--------------",
        next_steps,
        "",
        "Referencia",
        "----------",
        "Para detalle completo, ver `notes/memoria_canonica.txt` en el repo.",
    ]
    return "\n".join(summary).strip() + "\n"


def write_all(canonical: str, summary: str) -> None:
    targets = [
        (REPO_NOTES_DIR / "memoria_canonica.txt", canonical),
        (NOTES_DIR / "contexto para codex crackme.txt", canonical),
        (NOTES_DIR / "crackme_resumen_completo.txt", summary),
        (REPO_NOTES_DIR / "crackme_resumen_completo.txt", summary),
    ]
    for path, content in targets:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Synchronize external context txt files from the real crackme worklog.")
    ap.add_argument("--commit", action="store_true", help="Commit regenerated context files into the repo.")
    ap.add_argument("--push", action="store_true", help="Push after committing.")
    ap.add_argument("--message", default="Sync canonical crackme context", help="Commit message.")
    args = ap.parse_args()

    canonical = build_canonical()
    summary = build_summary()
    write_all(canonical, summary)

    if args.commit:
        subprocess.run(["git", "-C", str(REPO), "add", "notes"], check=True)
        subprocess.run(["git", "-C", str(REPO), "commit", "-m", args.message], check=True)
        if args.push:
            subprocess.run(["git", "-C", str(REPO), "push"], check=True)


if __name__ == "__main__":
    main()

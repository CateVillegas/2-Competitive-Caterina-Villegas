#!/usr/bin/env python3
"""
Competitive Intelligence Pipeline — Rappi México
=================================================
Un solo comando para correr todo el pipeline.

Uso rápido (demo con datos mock — Plan B garantizado):
    python main.py

Scraper real (requiere Playwright):
    python main.py --real --city cdmx --max-addresses 3 --visible

Solo análisis sobre datos ya existentes:
    python main.py --analysis-only
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

os.chdir(Path(__file__).parent)

# Fix Windows cp1252 encoding for Unicode output
if sys.stdout.encoding and sys.stdout.encoding.lower().startswith("cp"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def run(cmd, label):
    print(f"\n{'-'*55}")
    print(f">  {label}")
    print(f"{'-'*55}")
    r = subprocess.run(cmd, check=False)
    if r.returncode != 0:
        print(f"  '{label}' termino con codigo {r.returncode}")
    return r.returncode == 0


def main():
    p = argparse.ArgumentParser(description="Rappi CI Pipeline")
    p.add_argument("--real", action="store_true", help="Usar scraper real (requiere Playwright)")
    p.add_argument("--city", choices=["cdmx", "gdl", "mty"])
    p.add_argument("--max-addresses", type=int, default=25)
    p.add_argument("--visible", action="store_true")
    p.add_argument("--analysis-only", action="store_true")
    p.add_argument("--no-pdf", action="store_true")
    args = p.parse_args()

    print("=" * 55)
    print("  COMPETITIVE INTELLIGENCE — RAPPI MÉXICO")
    print("=" * 55)

    # Paso 1: Datos
    if not args.analysis_only:
        if args.real:
            cmd = [sys.executable, "scraper/competitive_scraper.py",
                   f"--max-addresses={args.max_addresses}"]
            if args.city:
                cmd.append(f"--city={args.city}")
            if args.visible:
                cmd.append("--visible")
            ok = run(cmd, "Scraper real (Playwright)")
            if not ok:
                print("  Scraper fallo -> usando datos mock como fallback")
                run([sys.executable, "scraper/generate_mock_data.py"], "Mock data (fallback)")
        else:
            run([sys.executable, "scraper/generate_mock_data.py"], "Generando datos mock (Plan B)")
    else:
        print("\n  --analysis-only: saltando scraping")

    # Verificar datos
    if not list(Path("data").glob("*.json")):
        print("No hay datos. Abortando.")
        sys.exit(1)

    # Paso 2: Análisis + charts
    analysis_cmd = [sys.executable, "analysis/generate_analysis.py"]
    if not args.real:
        analysis_cmd.append("--mock")
    run(analysis_cmd, "Generando análisis y charts")

    # Paso 3: PDF
    if not args.no_pdf:
        run([sys.executable, "analysis/generate_report_pdf.py"], "Generando PDF ejecutivo")

    # Resumen
    print("\n" + "=" * 55)
    print("  PIPELINE COMPLETADO")
    print("=" * 55)
    if Path("output").exists():
        for f in sorted(Path("output").iterdir()):
            print(f"  output/{f.name}  ({f.stat().st_size//1024} KB)")
    print()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Dashboard Generation System – Demo CLI

Ce script illustre l’usage de la classe `DashboardLLM`
pour produire des dashboards interactifs à partir de prompts
en langage naturel.

Fonctionnalités :
1. Démo automatisée sur 5 prompts prédéfinis
2. Test unitaire des outils (query_powerbi, select_ui_component, assemble_dashboard)
3. Mode interactif (prompt libre)
4. Mode “run all” (enchaîne les trois)

Logs :   ./dashboard gen/logs
HTML :   ./dashboard gen/generated_dashboards/…
"""

import os, sys, logging
from datetime import datetime
from DashboardLLM import DashboardLLM

# ───────────────────────────────────────────────────────────────
# 1) LOGGING
# ───────────────────────────────────────────────────────────────
def setup_logging() -> logging.Logger:
    log_dir = "dashboard gen"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "logs")

    fmt = (
        "%(asctime)s - %(name)s - %(levelname)s - "
        "%(funcName)s:%(lineno)d - %(message)s"
    )
    logging.basicConfig(
        level=logging.DEBUG,
        format=fmt,
        handlers=[
            logging.FileHandler(log_file, mode="a", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    lg = logging.getLogger(__name__)
    lg.info("=" * 80)
    lg.info(f"Starting Dashboard Demo – {datetime.now()}")
    lg.info("=" * 80)
    return lg


# ───────────────────────────────────────────────────────────────
# 2) AUTOMATED DEMO
# ───────────────────────────────────────────────────────────────
def demo_dashboard_generation(lg: logging.Logger) -> None:
    print("=" * 60, "\nDashboard Generation System Demo\n", "=" * 60, sep="")
    print("\n[1] Initializing DashboardLLM…")
    lg.info("Initializing DashboardLLM")
    try:
        llm = DashboardLLM()
    except Exception as e:
        lg.exception("Initialization failed")
        print(f"❌ {e}")
        return

    prompts = [
        "Montre-moi le CA mensuel 2024 et le top 5 produits",
        "Create a dashboard with availability KPIs and production by steel type",
        "Show me monthly revenue trends",
        "Display the top products and their production volumes",
        "Generate a comprehensive dashboard with all key metrics",
    ]

    for idx, prompt in enumerate(prompts, 1):
        lg.info("Prompt %s/%s: %s", idx, len(prompts), prompt)
        print(f"\n[{idx+1}] Processing prompt: “{prompt}”")
        print("-" * 50)
        try:
            res = llm.generate_dashboard_from_prompt(prompt, save_file=True)
            if res["filepath"]:
                print("✅ Dashboard generated!")
                print("📁", res["filepath"])
                print("🧩 Components:", res["components_used"])
                print(
                    "📝 HTML preview:",
                    (res["html_content"][:200] + "…")
                    if len(res["html_content"]) > 200
                    else res["html_content"],
                )
            else:
                print("❌ Failed – see logs for details.")
        except Exception:
            lg.exception("Error on prompt")
            print("❌ Exception – check logs.")
        print()


# ───────────────────────────────────────────────────────────────
# 3) TOOL TEST
# ───────────────────────────────────────────────────────────────
def test_individual_tools(lg: logging.Logger) -> None:
    print("\n" + "=" * 60 + "\nTesting Individual Dashboard Tools\n" + "=" * 60)
    try:
        llm = DashboardLLM()
    except Exception as e:
        lg.exception("LLM init failed (tools test)")
        print(f"❌ {e}")
        return

    # query_powerbi
    print("\n[1] query_powerbi")
    res = llm.execute_tool("query_powerbi", {"measure": "revenue_monthly"})
    print("✅", res)

    # select_ui_component
    print("\n[2] select_ui_component")
    res = llm.execute_tool("select_ui_component", {"data_shape": "timeseries"})
    print("✅", res)

    # assemble_dashboard
    print("\n[3] assemble_dashboard")
    comp = [
        {
            "component": "KPIBoxComponent",
            "props": {"title": "Test KPI", "value": 95.5, "delta": 2.3},
        }
    ]
    html = llm.execute_tool("assemble_dashboard", {"components": comp})
    print("✅ length:", len(html), "chars\n", html[:200], "…")


# ───────────────────────────────────────────────────────────────
# 4) INTERACTIVE PROMPT LOOP
# ───────────────────────────────────────────────────────────────
def interactive_mode(lg: logging.Logger) -> None:
    print("\n" + "=" * 60)
    print("Interactive Dashboard Generation Mode – type 'quit' to exit")
    print("=" * 60)

    try:
        llm = DashboardLLM()
    except Exception as e:
        lg.exception("LLM init failed (interactive)")
        print(f"❌ {e}")
        return

    while True:
        try:
            prompt = input("\n🎯 Prompt: ").strip()
            if prompt.lower() in {"quit", "exit", "q"}:
                print("👋 Bye!")
                return
            if not prompt:
                print("❌ Empty prompt.")
                continue

            res = llm.generate_dashboard_from_prompt(prompt, save_file=True)
            if res["filepath"]:
                print("✅ Dashboard →", res["filepath"])
            else:
                print("❌ Failed – see logs.")
        except KeyboardInterrupt:
            print("\n👋 Bye!")
            break
        except Exception:
            lg.exception("Error during interactive loop")
            print("❌ Exception – check logs.")


# ───────────────────────────────────────────────────────────────
# 5) MAIN MENU
# ───────────────────────────────────────────────────────────────
def main() -> None:
    lg = setup_logging()

    os.makedirs("dashboard gen/generated_dashboards", exist_ok=True)
    print("🚀 Welcome to the Dashboard Generation System Demo!")

    menu = (
        "\nAvailable modes:\n"
        "1. Automated demo\n"
        "2. Test individual tools\n"
        "3. Interactive mode\n"
        "4. Run all\n"
        "\nSelect (1-4): "
    )
    choice = input(menu).strip()

    if choice == "1":
        demo_dashboard_generation(lg)
    elif choice == "2":
        test_individual_tools(lg)
    elif choice == "3":
        interactive_mode(lg)
    elif choice == "4":
        demo_dashboard_generation(lg)
        test_individual_tools(lg)
        interactive_mode(lg)
    else:
        print("❌ Invalid – running automated demo.")
        demo_dashboard_generation(lg)

    lg.info("Demo session finished.")


if __name__ == "__main__":
    main()

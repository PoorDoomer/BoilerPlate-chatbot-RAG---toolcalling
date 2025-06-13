# tools.py
from __future__ import annotations
from typing import Optional, List, Dict, Any, Tuple
import datetime
import json
import sqlite3
import os
from jinja2 import Environment, FileSystemLoader, select_autoescape
from functools import lru_cache   # NEW

SCHEMA_PATH = "databasevf_schema.json"   # adapte si besoin
TEMPLATES_DIR = "dashboardgen/templates"
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────
#  A.  Helpers UI que l'agent peut chaîner plus facilement
# ─────────────────────────────────────────────────────────────
def make_kpi(title: str, value: float, delta: Optional[float] = None) -> Dict[str, Any]:
    return {
        "component": "KPIBoxComponent",
        "props": {"title": title, "value": value, "delta": delta},
    }

def make_line(labels: List[str], series: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "component": "LineChartComponent",
        "props": {"labels": labels, "series": series},
    }
    
def make_multi_series_chart(chart_data_list: List[Dict[str, Any]], title: str = None) -> Dict[str, Any]:
    """
    Combine multiple chart data objects into a single multi-series chart.
    Useful for merging data loaded from scratchpad.
    
    Args:
        chart_data_list (List[Dict]): List of chart data objects with labels and series
        title (str): Optional chart title
        
    Returns:
        Dict: A properly formatted line chart component
    """
    if not chart_data_list:
        return make_line([], [])
        
    # Use the first dataset's labels as the base
    base_labels = chart_data_list[0]["labels"]
    all_series = []
    
    # Collect all series from all datasets
    for data in chart_data_list:
        for series in data["series"]:
            all_series.append(series)
    
    result = make_line(base_labels, all_series)
    
    # Add title if provided
    if title and "props" in result:
        result["props"]["title"] = title
        
    return result

def make_table(headers: List[str], rows: List[Tuple[Any, ...]]) -> Dict[str, Any]:
    return {
        "component": "TableComponent",
        "props": {"headers": headers, "rows": [list(r) for r in rows]},
    }

# ─────────────────────────────────────────────────────────────
#  B.  Cache léger sur le schéma DB (évite les re-downloads)
# ─────────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def _load_schema() -> Dict[str, Any]:
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class Tools:
    """
    Ensemble de fonctions exposées comme « tools » au modèle ReAct.
    Toutes les méthodes publiques (non _private et non __dunder) seront
    enregistrées automatiquement par LLM.register_tools_from_class().
    """

    # ──────────────────────────────────────────────
    # SECTION 1 – Méta-données / schéma de la base
    # ──────────────────────────────────────────────
    def get_db_schema(self) -> Dict[str, Any]:
        """
        Renvoie le schéma complet de la base, tel que stocké dans
        `databasevf_schema.json`.

        Returns
        -------
        dict
            Le JSON désérialisé représentant la structure de la DB.
        """
        return _load_schema()

    def list_tables(self) -> List[str]:
        """
        Liste toutes les tables présentes dans la base.

        Returns
        -------
        list[str]
        """
        return list(self.get_db_schema().get("tables", {}).keys())

    def describe_table(self, table_name: str) -> Dict[str, Any]:
        """
        Renvoie la structure (colonnes, types…) d'une table donnée.

        Parameters
        ----------
        table_name : str
            Nom exact de la table (sensible à la casse).

        Returns
        -------
        dict
            Description détaillée de la table.

        Raises
        ------
        KeyError
            Si la table n'existe pas.
        """
        schema = self.get_db_schema().get("tables", {})
        if table_name not in schema:
            raise KeyError(f"Table '{table_name}' inconnue.")
        return schema[table_name]

    # (optionnel) Pour de petites requêtes ad-hoc sans passer par sql_query
    def quick_count(self, table_name: str) -> int:
        """
        Compte le nombre de lignes d'une table.

        Parameters
        ----------
        table_name : str

        Returns
        -------
        int
        """
        conn = sqlite3.connect("databasevf.db")
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM \"{table_name}\"")
        n, = cur.fetchone()
        conn.close()
        return n

    # ──────────────────────────────────────────────
    # SECTION 2 – KPI & calculs industriels existants
    # ──────────────────────────────────────────────
    def calculate_taux_disponibilite(
        self, temps_requis: float, somme_des_arrets: float
    ) -> float:
        """… (inchangé) …"""
        if temps_requis == 0:
            return 0.0
        return ((temps_requis - somme_des_arrets) / temps_requis) * 100

    def calculate_temps_requis_pourcentage(
        self, temps_ouverture: float, somme_des_arrets_programmes: float
    ) -> float:
        """… (inchangé) …"""
        if temps_ouverture == 0:
            return 0.0
        return ((temps_ouverture - somme_des_arrets_programmes) / temps_ouverture) * 100

    def calculate_mtbf(
        self, temps_requis: float, somme_des_arrets: float, nombre_des_arrets: int
    ) -> float:
        """… (inchangé) …"""
        return (temps_requis - somme_des_arrets) / (nombre_des_arrets + 1)

    def calculate_mttr(self, somme_des_arrets: float, nombre_des_arrets: int) -> float:
        """… (inchangé) …"""
        if nombre_des_arrets == 0:
            return 0.0
        return somme_des_arrets / nombre_des_arrets

    def calculate_rendement(self, poids_brames: float, poids_ferrailles: float) -> float:
        """… (inchangé) …"""
        if poids_ferrailles == 0:
            return 0.0
        return (poids_brames / poids_ferrailles) * 100

    def calculate_conso_elec(self, cons_elec_eaf: float, cons_elec_lf: float) -> float:
        """… (inchangé) …"""
        return cons_elec_eaf + cons_elec_lf

    def calculate_temps_requis(
        self, temps_ouverture: float, somme_des_arrets_programmes: float
    ) -> float:
        """… (inchangé) …"""
        return temps_ouverture - somme_des_arrets_programmes

    # ──────────────────────────────────────────────
    # SECTION 3 – Outils date & durée
    # ──────────────────────────────────────────────
    @staticmethod
    def convert_to_datetime(date_string: str) -> Optional[datetime.datetime]:
        """… (inchangé) …"""
        try:
            return datetime.datetime.fromisoformat(date_string.rstrip("Z"))
        except ValueError:
            try:
                return datetime.datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return None

    def calculate_duration_hours(
        self, start_time: str, end_time: str
    ) -> Optional[float]:
        """… (inchangé) …"""
        start_dt = self.convert_to_datetime(start_time)
        end_dt = self.convert_to_datetime(end_time)
        if start_dt is None or end_dt is None:
            return None
        return (end_dt - start_dt).total_seconds() / 3600

    # ──────────────────────────────────────────────
    # SECTION 4 – Nouveaux KPI « énergie » utiles
    # ──────────────────────────────────────────────
    def calculate_energy_intensity(
        self, conso_elec_kwh: float, poids_brames_tonnes: float
    ) -> float:
        """
        kWh consommés par tonne produite.

        Parameters
        ----------
        conso_elec_kwh : float
        poids_brames_tonnes : float

        Returns
        -------
        float
        """
        if poids_brames_tonnes == 0:
            return 0.0
        return conso_elec_kwh / poids_brames_tonnes
    # ──────────────────────────────────────────────
    # SECTION 5 – KPI production & qualité
    # ──────────────────────────────────────────────
    def calculate_performance_rate(
        self, production_reelle_t: float, cadence_theorique_t: float
    ) -> float:
        """
        Performance = Production réelle / Cadence théorique × 100.

        Parameters
        ----------
        production_reelle_t : float   # tonnes produites
        cadence_theorique_t : float   # tonnes théoriques (objectif)

        Returns
        -------
        float
            Taux de performance (%). 0 si cadence_theorique_t = 0.
        """
        if cadence_theorique_t == 0:
            return 0.0
        return (production_reelle_t / cadence_theorique_t) * 100

    def calculate_quality_rate(
        self, pieces_conformes: int, pieces_totales: int
    ) -> float:
        """
        Qualité = Pièces conformes / Pièces totales × 100.
        """
        if pieces_totales == 0:
            return 0.0
        return (pieces_conformes / pieces_totales) * 100

    def calculate_oee(
        self,
        taux_disponibilite: float,
        performance_rate: float,
        quality_rate: float
    ) -> float:
        """
        Overall Equipment Effectiveness (%) = (D × P × Q) / 10000
        car chaque sous-taux est sur 100.
        """
        return (taux_disponibilite * performance_rate * quality_rate) / 10000

    def calculate_maintenance_cost_per_tonne(
        self, cout_total_eur: float, tonnage: float
    ) -> float:
        """
        Coût de maintenance par tonne d'acier produite (€/t).
        """
        if tonnage == 0:
            return 0.0
        return cout_total_eur / tonnage

    # ──────────────────────────────────────────────
    # SECTION 6 – Helpers statistiques / séries temps
    # ──────────────────────────────────────────────
    def moving_average(self, values: list[float], window: int) -> list[float]:
        """
        Moyenne mobile centrée vers l'arrière.
        Les premières valeurs (< window) sont renvoyées inchangées.
        """
        ma: list[float] = []
        for i, _ in enumerate(values):
            if i < window - 1:
                ma.append(values[i])
            else:
                ma.append(sum(values[i - window + 1 : i + 1]) / window)
        return ma

    def zscore(self, values: list[float]) -> list[float]:
        """
        Z-score normalisation : (x - µ) / σ.
        """
        if not values:
            return []
        mean_val = sum(values) / len(values)
        std = (sum((v - mean_val) ** 2 for v in values) / len(values)) ** 0.5
        return [(v - mean_val) / std if std != 0 else 0.0 for v in values]

    def detect_outliers(
        self, values: list[float], method: str = "IQR", threshold: float = 1.5
    ) -> list[int]:
        """
        Renvoie la liste des indices considérés comme outliers.
        method='IQR' ou 'zscore'.
        """
        out = []
        if method == "zscore":
            zs = self.zscore(values)
            out = [i for i, z in enumerate(zs) if abs(z) > threshold]
        else:  # IQR par défaut
            q1 = sorted(values)[len(values) // 4]
            q3 = sorted(values)[3 * len(values) // 4]
            iqr = q3 - q1
            lo, hi = q1 - threshold * iqr, q3 + threshold * iqr
            out = [i for i, v in enumerate(values) if v < lo or v > hi]
        return out

    def normalize_series(
        self, values: list[float], method: str = "minmax"
    ) -> list[float]:
        """
        min-max ou zscore (choisir via `method`)
        """
        if not values:
            return []
        if method == "zscore":
            return self.zscore(values)
        vmin, vmax = min(values), max(values)
        if vmax == vmin:
            return [0.0] * len(values)
        return [(v - vmin) / (vmax - vmin) for v in values]

    # ──────────────────────────────────────────────
    # SECTION 7 – Helpers SQL rapides
    # ──────────────────────────────────────────────
    def filter_table(self, table_name: str, where_clause: str) -> list[tuple]:
        """
        SELECT * FROM table WHERE …  (petite requête utilitaire).

        Exemple : where_clause="GRADE='A42' AND HEATID>1000".
        """
        conn = sqlite3.connect("databasevf.db")
        cur = conn.cursor()
        query = f"SELECT * FROM \"{table_name}\" WHERE {where_clause}"
        cur.execute(query)
        rows = cur.fetchall()
        conn.close()
        return rows
        
    def get_timeseries_data_for_chart(
        self, 
        table_name: str, 
        date_col: str, 
        value_col: str, 
        agg_func: str = "SUM",
        date_format: str = "%Y-%m-%d",
        where_clause: str = None
    ) -> Dict[str, Any]:
        """
        Exécute une requête SQL pour agréger des données par jour et les formate
        directement pour un graphique en ligne. Renvoie un dictionnaire prêt à l'emploi.
        
        Args:
            table_name (str): Nom de la table
            date_col (str): Nom de la colonne date
            value_col (str): Nom de la colonne valeur à agréger
            agg_func (str): Fonction d'agrégation (SUM, AVG, MAX, MIN)
            date_format (str): Format de date pour le regroupement
            where_clause (str): Clause WHERE optionnelle
            
        Returns:
            Dict[str, Any]: Données formatées pour un graphique en ligne
        """
        conn = sqlite3.connect("databasevf.db")
        cur = conn.cursor()
        
        where_part = f"WHERE {where_clause}" if where_clause else ""
        
        query = f"""
            SELECT 
                strftime('{date_format}', "{date_col}") as day, 
                {agg_func}("{value_col}") as value
            FROM "{table_name}"
            {where_part}
            GROUP BY day
            ORDER BY day
        """
        
        print(f"[DEBUG] Executing timeseries query: {query}")
        cur.execute(query)
        rows = cur.fetchall()
        conn.close()
        
        # Format data for chart
        labels = [row[0] for row in rows]
        data = [row[1] for row in rows]
        
        print(f"[DEBUG] Timeseries data generated with {len(labels)} points")
        
        return {
            "labels": labels, 
            "series": [{"name": value_col, "data": data}]
        }

    def aggregate_table(
        self,
        table_name: str,
        group_by_cols: list[str],
        agg_col: str,
        agg_func: str = "SUM",
    ) -> list[tuple]:
        """
        Agrégation simple (SUM, AVG, MAX…).
        Gère correctement les cas avec ou sans colonnes de groupage.
        """
        conn = sqlite3.connect("databasevf.db")
        cur = conn.cursor()
        
        # Handle empty group_by_cols case
        if not group_by_cols:
            # Case: No grouping, calculate for the whole table
            query = f"SELECT {agg_func}(\"{agg_col}\") FROM \"{table_name}\""
        else:
            # Case: Grouping by specified columns
            group_expr = ", ".join([f'"{col}"' for col in group_by_cols])
            query = (
                f"SELECT {group_expr}, {agg_func}(\"{agg_col}\") "
                f"FROM \"{table_name}\" GROUP BY {group_expr}"
            )
            
        cur.execute(query)
        rows = cur.fetchall()
        conn.close()
        return rows

    # ──────────────────────────────────────────────
    # SECTION 8 – Conversion d'unités énergie
    # ──────────────────────────────────────────────
    def convert_energy_unit(
        self, value: float, from_unit: str, to_unit: str
    ) -> float:
        """
        kWh ⇄ MWh ⇄ GJ  (1 kWh = 0.0036 GJ).

        Units acceptées : 'kwh', 'mwh', 'gj' (insensible à la casse).
        """
        u = from_unit.lower()
        v = to_unit.lower()

        # Convert to kWh interne
        if u == v:
            return value
        if u == "mwh":
            value *= 1000
            u = "kwh"
        if u == "gj":
            value /= 0.0036
            u = "kwh"

        # kWh → cible
        if v == "kwh":
            return value
        if v == "mwh":
            return value / 1000
        if v == "gj":
            return value * 0.0036

        raise ValueError("Unités acceptées : kWh, MWh, GJ")
    @staticmethod
    def select_ui_component(data_shape: str) -> str:
        """
        Map data type to appropriate UI component.
        
        Args:
            data_shape (str): The data type ('timeseries', 'kpi', 'table', 'pie', 'bar', 'card')
            
        Returns:
            str: The component name to use
            
        Available mappings:
            - timeseries -> LineChartComponent
            - kpi -> KPIBoxComponent
            - table -> TableComponent
            - pie -> PieChartComponent
            - bar -> BarChartComponent
            - card -> CardListComponent
        """
        mapping = {
            "timeseries": "LineChartComponent",
            "kpi": "KPIBoxComponent", 
            "table": "TableComponent",
            "pie": "PieChartComponent",
            "bar": "BarChartComponent",
            "card": "CardListComponent"
        }
        return mapping.get(data_shape, "TableComponent")

    @staticmethod
    def assemble_dashboard(
        components: List[Dict[str, Any]],
        *,
        title: str = "Dashboard de production",
        theme: str = "light",
        outfile: str = "dashboard.html",
    ) -> str:
        """
        Génère le HTML dans `outfile` et renvoie le chemin absolu.
        
        IMPORTANT: Les composants DOIVENT être créés en utilisant les helpers
        (ex: make_kpi, make_line) pour garantir le bon format.
        Ne pas inventer de structure JSON.

        Parameters
        ----------
        components : list[dict]
        title      : str   — Titre affiché en haut de page
        theme      : str   — 'light' (défaut) ou 'dark'
        outfile    : str   — Nom du fichier de sortie
        """
        env = Environment(
            loader=FileSystemLoader(TEMPLATES_DIR),
            autoescape=select_autoescape(["html"])
        )

        # Première exécution : on dépose le template de base si absent
        tpl_path = os.path.join(TEMPLATES_DIR, "dashboard.html")
        if not os.path.exists(tpl_path):
            with open(tpl_path, "w", encoding="utf-8") as f:
                f.write(_DEFAULT_TEMPLATE_STR)  # voir ci-dessous

        template = env.get_template("dashboard.html")
        html = template.render(
            page_title=title,
            components_json=json.dumps(components, ensure_ascii=False, indent=None),
            theme=theme,
        )

        with open(outfile, "w", encoding="utf-8") as f:
            f.write(html)

        return os.path.abspath(outfile)

# -----------------------------------------------------------------
#  C.  Template de base (une seule fois) – ultra simplifié
# -----------------------------------------------------------------
_DEFAULT_TEMPLATE_STR = """
<!DOCTYPE html>
<html lang="fr" data-theme="{{ theme }}">
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>{{ page_title }}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
      :root {
        --bg: #f5f5f5; --fg: #333;
        --card-bg: #fff; --card-shadow: rgba(0,0,0,.1);
      }
      [data-theme="dark"] {
        --bg:#1e1e1e; --fg:#eee; --card-bg:#2a2a2a; --card-shadow: rgba(0,0,0,.6);
      }
      body{margin:0;background:var(--bg);font:16px "Segoe UI",sans-serif;color:var(--fg);}
      #app{display:grid;gap:20px;padding:25px;grid-template-columns:repeat(auto-fit,minmax(380px,1fr));}
      .component-container{background:var(--card-bg);padding:20px;border-radius:10px;box-shadow:0 2px 4px var(--card-shadow);}
      .kpi-container{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;}
      .kpi-value{font-size:2.7rem;font-weight:700;color:#2196F3}
      .kpi-title{margin-bottom:6px;font-weight:500;opacity:.8}
      table{width:100%;border-collapse:collapse}
      th,td{padding:6px 8px;border:1px solid #ddd}
      th{background:rgba(0,0,0,.05);text-align:left}
    </style>
</head>
<body>
  <h1 style="text-align:center;margin:20px 0">{{ page_title }}</h1>
  <div id="app"></div>
<script type="module">
  const components={{ components_json }};
  const root=document.getElementById('app');

  /* Library */
  const C = {
    KPIBoxComponent:{render(el,p){el.className+=' kpi-container';el.innerHTML=
      `<div class="kpi-title">${p.title}</div><div class="kpi-value">${p.value}${p.delta!=null?` (${p.delta>0?'+':''}${p.delta})`:''}</div>`;}},
    LineChartComponent:{render(el,p){const c=_canvas(el);new Chart(c,{type:'line',
      data:{labels:p.labels,datasets:p.series.map((s,i)=>({label:s.name,data:s.data,
             borderColor:`hsl(${i*137.5},70%,50%)`,backgroundColor:`hsla(${i*137.5},70%,50%,.15)`,
             tension:.35}))},options:{responsive:true}});}},
    TableComponent:{render(el,p){const t=document.createElement('table');
      t.innerHTML=`<thead>${_row('th',p.headers)}</thead><tbody>${p.rows.map(r=>_row('td',r)).join('')}</tbody>`;
      el.appendChild(t);}}
  };
  function _canvas(el){const c=document.createElement('canvas');el.appendChild(c);return c}
  function _row(tag,cells){return `<tr>${cells.map(c=>`<${tag}>${c}</${tag}>`).join('')}</tr>`}

  /* Component type mapping */
  const component_mapping = {
    "kpi": "KPIBoxComponent",
    "line": "LineChartComponent",
    "bar": "BarChartComponent",
    "pie": "PieChartComponent",
    "table": "TableComponent",
    "card": "CardListComponent"
  };
  
  /* Render loop with format adaptation */
  components.forEach((item)=>{
    // Check for the AI's simplified format first
    const componentName = item.component || component_mapping[item.type];
    const props = item.props || item; // If no props, pass the whole item
    
    const box=document.createElement('div');box.className='component-container';
    root.appendChild(box);
    
    if (!componentName) {
      box.textContent = `❓ Format inconnu: ${JSON.stringify(item).substring(0,50)}...`;
      return;
    }
    
    (C[componentName]||{render:(e)=>e.textContent=`❓ Composant inconnu: ${componentName}`}).render(box,props);
  });
</script>
</body>
</html>
"""

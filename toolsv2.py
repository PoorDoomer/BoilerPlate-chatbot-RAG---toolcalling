# --- Filename: tools_v2.py ---

from __future__ import annotations
import os
import sqlite3
import json
from typing import Optional, List, Dict, Any, Tuple
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Import the tool decorator from your agent file
from ulti_llm import tool

# --- Configuration (remains the same) ---
SCHEMA_PATH = "databasevf_schema.json"
TEMPLATES_DIR = "dashboardgen/templates"
if not os.path.exists(TEMPLATES_DIR):
    os.makedirs(TEMPLATES_DIR)

# --- UI Component Helpers (Not tools, so no decorator) ---
# These are used by other tools, but not called by the agent directly.
def make_kpi(title: str, value: float, unit: str = "", delta: Optional[float] = None) -> Dict[str, Any]:
    return {"component": "KPIBoxComponent", "props": {"title": title, "value": f"{value:,.2f} {unit}".strip(), "delta": delta}}

def make_line(labels: List[str], series: List[Dict[str, Any]], title: Optional[str] = None) -> Dict[str, Any]:
    return {"component": "LineChartComponent", "props": {"title": title, "labels": labels, "series": series}}

def make_table(headers: List[str], rows: List[Tuple[Any, ...]]) -> Dict[str, Any]:
    return {"component": "TableComponent", "props": {"headers": headers, "rows": [list(r) for r in rows]}}


# --- Main Tools Class ---
# The agent will get an instance of this class.
class SteelMillTools:
    """A collection of domain-specific tools for steel mill analytics."""

    # Note: No __init__ needed unless you have state to manage here.

    @tool("Get the full database schema as a JSON object.")
    def get_db_schema(self) -> Dict[str, Any]:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    @tool("Execute a read-only SQL query against the steel mill database.")
    def query_database(self, query: str) -> List[Dict]:
        """Runs a SQL query and returns a list of dictionaries."""
        conn = sqlite3.connect('databasevf.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query)
        result = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return result

    @tool("Get aggregated time-series data, formatted for a chart.")
    def get_timeseries_data(self, table_name: str, date_col: str, value_col: str, agg_func: str = "SUM") -> Dict:
        """Fetches daily aggregated data and formats it perfectly for a line chart."""
        rows = self.query_database(f"""
            SELECT strftime('%Y-%m-%d', "{date_col}") as day, {agg_func}("{value_col}") as value
            FROM "{table_name}" WHERE "{date_col}" IS NOT NULL GROUP BY day ORDER BY day
        """)
        return {
            "labels": [row["day"] for row in rows],
            "series": [{"name": value_col.replace("_", " ").title(), "data": [row["value"] for row in rows]}]
        }

    @tool("Calculates the total electrical consumption from EAF and LF values.")
    def calculate_total_consumption(self, cons_eaf_kwh: float, cons_lf_kwh: float) -> float:
        return cons_eaf_kwh + cons_lf_kwh

    @tool("Assembles and generates a dashboard HTML file from a list of UI components.")
    def assemble_dashboard(self,
                           components: List[Dict[str, Any]],
                           title: str = "Steel Mill Production Dashboard",
                           outfile: str = "dashboard.html") -> str:
        """
        Takes a list of components (from make_kpi, make_line, etc.) and generates a dashboard file.
        Returns the absolute path to the generated file.
        """
        # (Your assemble_dashboard logic here, unchanged)
        env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=select_autoescape(["html"]))
        if not os.path.exists(os.path.join(TEMPLATES_DIR, "dashboard.html")):
            with open(os.path.join(TEMPLATES_DIR, "dashboard.html"), "w", encoding="utf-8") as f:
                f.write(_DEFAULT_TEMPLATE_STR)
        template = env.get_template("dashboard.html")
        html = template.render(
            page_title=title,
            components_json=json.dumps(components, ensure_ascii=False, indent=None),
            theme='light'
        )
        with open(outfile, "w", encoding="utf-8") as f:
            f.write(html)
        return f"Dashboard successfully generated at: {os.path.abspath(outfile)}"

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

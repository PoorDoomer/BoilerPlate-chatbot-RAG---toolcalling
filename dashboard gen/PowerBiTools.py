import requests
import json
import sqlite3
from typing import Dict, List, Optional, Any
from jinja2 import Environment, FileSystemLoader
import os
from datetime import datetime

# Global schema cache
_SCHEM = None

def load_schema(path="databasevf_schema.json") -> dict:
    global _SCHEM
    if _SCHEM is None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                _SCHEM = json.load(f)
        except FileNotFoundError:
            # Fallback to empty schema if file doesn't exist
            _SCHEM = {}
    return _SCHEM

SCHEMA = load_schema() 

MEASURE_ROUTER = {
    "revenue_monthly": {
        "sql": (
            "SELECT strftime('%Y-%m', CUT_TIME) AS month, "
            "SUM(PIECE_WEIGHT_MEAS)                              AS revenue "
            "FROM \"05-CCM-Brame\" "
            "WHERE strftime('%Y', CUT_TIME) = :year "
            "GROUP BY 1 ORDER BY 1"
        ),
        "type": "timeseries",
        "x": "month", "y": "revenue"
    },
    "top_products": {
        "sql": (
            "SELECT STEELGRADECODE_ACT         AS product, "
            "SUM(TAPPING_WEIGHT)               AS total_production "
            "FROM \"02-EAF\" "
            "WHERE strftime('%Y', HEATANNOUNCE_ACT) = :year "
            "GROUP BY product "
            "ORDER BY total_production DESC "
            "LIMIT :top_n"
        ),
        "type": "table"
    },
    "availability_kpi": {
        "sql": (
            "SELECT ROUND(AVG(((POWER_ON_DUR) / "
            "(POWER_ON_DUR + POWER_OFF_DUR)) * 100), 2) AS availability "
            "FROM \"02-EAF\" "
            "WHERE date(HEATANNOUNCE_ACT) >= date('now','-30 day')"
        ),
        "type": "kpi",
        "title": "Disponibilité EAF (%)"
    },
    "production_by_type": {
        "sql": (
            "SELECT STEELGRADECODE_ACT AS category, "
            "SUM(TAPPING_WEIGHT)      AS value "
            "FROM \"02-EAF\" "
            "WHERE date(HEATANNOUNCE_ACT) >= date('now','-90 day') "
            "GROUP BY category "
            "ORDER BY value DESC "
            "LIMIT 6"
        ),
        "type": "pie"
    },
}

def query_powerbi(
    measure: str,
    year: str | int | None = None,
    top_n: int = 5,
    **kwargs
) -> Dict[str, Any]:
    """
    Exécute une requête *pré-mappée* sur la base SQLite et renvoie
    un payload prêt à être rendu par le dashboard builder.

    Parameters
    ----------
    measure : str
        **Slug métier** à interroger (voir liste ci-dessous).
    year : int | str, optional
        Année à filtrer pour les mesures temporelles
        (par défaut, l'année courante).
    top_n : int, optional
        Limite de lignes pour les mesures "top" (défaut=5).

    Mesures disponibles
    -------------------
    • **revenue_monthly**      → table *05-CCM-Brame* ; somme `PIECE_WEIGHT_MEAS`
    • **top_products**         → table *02-EAF*       ; somme `TAPPING_WEIGHT`
    • **availability_kpi**     → table *02-EAF*       ; ratio Power On / Total
    • **production_by_type**   → table *02-EAF*       ; distribution `TAPPING_WEIGHT`

    Returns
    -------
    dict
        *type*  : "timeseries" | "table" | "kpi" | "pie"  
        *data*  : structure adaptée au composant frontend.

    Notes
    -----
    - Aucun nombre n'est formaté avec séparateur ou espace (exigence système).
    - Les erreurs SQL sont renvoyées sous forme de table.
    """
    measure = measure.lower().strip()
    if measure not in MEASURE_ROUTER:
        return {
            "type": "table",
            "data": {"headers": ["Error"],
                     "rows": [[f"Unknown measure '{measure}'"]]}
        }

    cfg  = MEASURE_ROUTER[measure]
    sql  = cfg["sql"]
    year = str(year or datetime.now().year)

    conn = sqlite3.connect("databasevf.db")
    cur  = conn.cursor()
    try:
        cur.execute(sql, {"year": year, "top_n": top_n})
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
    except sqlite3.Error as e:
        return {
            "type": "table",
            "data": {"headers": ["SQL error"], "rows": [[str(e)]]}
        }
    finally:
        conn.close()

    # ---------- post-processing ----------
    if cfg["type"] == "timeseries":
        labels = [str(r[0]) for r in rows]
        values = [float(r[1] or 0) for r in rows]
        return {
            "type": "timeseries",
            "data": {
                "labels": labels,
                "series": [{"name": cfg["y"], "data": values}],
            },
        }

    if cfg["type"] == "pie":
        labels = [str(r[0]) for r in rows]
        values = [float(r[1] or 0) for r in rows]
        return {"type": "pie", "data": {"labels": labels, "values": values}}

    if cfg["type"] == "kpi":
        value = float(rows[0][0] or 0)
        return {
            "type": "kpi",
            "data": {"title": cfg.get("title", cols[0]),
                     "value": value, "delta": None},
        }

    # Fallback → table
    return {
        "type": "table",
        "data": {
            "headers": cols,
            "rows": [[str(c or "") for c in r] for r in rows],
        },
    }

def select_ui_component(data_shape: str) -> str:
    """
    Map data type to appropriate UI component.
    
    Args:
        data_shape (str): The data type ('timeseries', 'kpi', 'table', 'pie')
        
    Returns:
        str: The component name to use
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


def assemble_dashboard(components: List[Dict[str, Any]]) -> str:
    """
    Assemble multiple components into a complete HTML dashboard.
    
    Args:
        components (List[Dict]): List of component specifications
            [ { "component": "LineChartComponent", "props": {...} }, ... ]
            
    Returns:
        str: Complete HTML dashboard as string
    """
    try:
        # Create templates directory if it doesn't exist
        templates_dir = "dashboard gen/templates"
        os.makedirs(templates_dir, exist_ok=True)
        
        # Use string template for now, will create proper template file
        dashboard_template = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Interactif</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="/static/styles.css"/>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        #app {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            max-width: 1200px;
            margin: 0 auto;
        }
        .component-container {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            min-height: 300px;
        }
        .kpi-container {
            min-height: 150px;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
        }
        .kpi-value {
            font-size: 2.5em;
            font-weight: bold;
            color: #2196F3;
        }
        .kpi-title {
            font-size: 1.2em;
            color: #666;
            margin-bottom: 10px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        th {
            background-color: #f2f2f2;
            font-weight: bold;
        }
        canvas {
            max-width: 100%;
            height: auto;
        }
    </style>
</head>
<body>
    <h1 style="text-align: center; color: #333; margin-bottom: 30px;">Dashboard de Production</h1>
    <div id="app"></div>

    <script type="module">
        const components = {{ components_json }};
        const root = document.getElementById('app');

        // Component implementations
        const ComponentLibrary = {
            LineChartComponent: {
                render(element, props) {
                    const canvas = document.createElement('canvas');
                    canvas.width = 400;
                    canvas.height = 200;
                    element.appendChild(canvas);
                    
                    const ctx = canvas.getContext('2d');
                    new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: props.labels,
                            datasets: props.series.map((serie, index) => ({
                                label: serie.name,
                                data: serie.data,
                                borderColor: `hsl(${index * 137.5}, 70%, 50%)`,
                                backgroundColor: `hsla(${index * 137.5}, 70%, 50%, 0.1)`,
                                tension: 0.4
                            }))
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {
                                y: {
                                    beginAtZero: true
                                }
                            }
                        }
                    });
                }
            },
            
            PieChartComponent: {
                render(element, props) {
                    const canvas = document.createElement('canvas');
                    canvas.width = 300;
                    canvas.height = 300;
                    element.appendChild(canvas);
                    
                    const ctx = canvas.getContext('2d');
                    new Chart(ctx, {
                        type: 'pie',
                        data: {
                            labels: props.labels,
                            datasets: [{
                                data: props.values,
                                backgroundColor: props.labels.map((_, index) => 
                                    `hsl(${index * 137.5}, 70%, 60%)`
                                )
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false
                        }
                    });
                }
            },
            
            KPIBoxComponent: {
                render(element, props) {
                    element.className += ' kpi-container';
                    element.innerHTML = `
                        <div>
                            <div class="kpi-title">${props.title}</div>
                            <div class="kpi-value">${props.value}${props.delta !== null ? ` (${props.delta > 0 ? '+' : ''}${props.delta})` : ''}</div>
                        </div>
                    `;
                }
            },
            
            TableComponent: {
                render(element, props) {
                    const table = document.createElement('table');
                    
                    // Headers
                    const thead = document.createElement('thead');
                    const headerRow = document.createElement('tr');
                    props.headers.forEach(header => {
                        const th = document.createElement('th');
                        th.textContent = header;
                        headerRow.appendChild(th);
                    });
                    thead.appendChild(headerRow);
                    table.appendChild(thead);
                    
                    // Rows
                    const tbody = document.createElement('tbody');
                    props.rows.forEach(row => {
                        const tr = document.createElement('tr');
                        row.forEach(cell => {
                            const td = document.createElement('td');
                            td.textContent = cell;
                            tr.appendChild(td);
                        });
                        tbody.appendChild(tr);
                    });
                    table.appendChild(tbody);
                    
                    element.appendChild(table);
                }
            },
            
            BarChartComponent: {
                render(element, props) {
                    const canvas = document.createElement('canvas');
                    canvas.width = 400;
                    canvas.height = 200;
                    element.appendChild(canvas);
                    
                    const ctx = canvas.getContext('2d');
                    new Chart(ctx, {
                        type: 'bar',
                        data: {
                            labels: props.labels,
                            datasets: props.series.map((serie, index) => ({
                                label: serie.name,
                                data: serie.data,
                                backgroundColor: `hsla(${index * 137.5}, 70%, 60%, 0.8)`,
                                borderColor: `hsl(${index * 137.5}, 70%, 50%)`,
                                borderWidth: 1
                            }))
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            scales: {
                                y: {
                                    beginAtZero: true
                                }
                            }
                        }
                    });
                }
            }
        };

        // Render all components
        components.forEach(({component, props}) => {
            const container = document.createElement('div');
            container.className = 'component-container';
            root.appendChild(container);
            
            if (ComponentLibrary[component]) {
                ComponentLibrary[component].render(container, props);
            } else {
                container.innerHTML = `<p>Component ${component} not found</p>`;
            }
        });
    </script>
</body>
</html>
        """
        
        # Replace the components placeholder with actual JSON
        components_json = json.dumps(components, indent=2)
        html_content = dashboard_template.replace("{{ components_json }}", components_json)
        with open("dashboard.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        return html_content
        
    except Exception as e:
        return f"<html><body><h1>Error assembling dashboard: {str(e)}</h1></body></html>"

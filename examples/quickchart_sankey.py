import json
from urllib.parse import quote_plus

import requests


def build_quickchart_url(chart_config: dict, *, width: int = 1200, height: int = 800,
                         background: str = "transparent", plugins: list[str] | None = None,
                         chart_js_version: str | int = 3, use_short_url: bool = False,
                         session: requests.Session | None = None) -> str:
    """Generate a QuickChart URL for a given chart configuration."""

    base_url = "https://quickchart.io/chart"
    encoded_chart = quote_plus(json.dumps(chart_config, ensure_ascii=False))

    params = [
        f"chart={encoded_chart}",
        f"width={width}",
        f"height={height}",
        f"background={quote_plus(background)}",
        f"version={chart_js_version}"
    ]

    if plugins:
        params.append(f"plugins={quote_plus(','.join(plugins))}")

    long_url = f"{base_url}?{'&'.join(params)}"

    if not use_short_url:
        return long_url

    payload = {
        "chart": chart_config,
        "width": width,
        "height": height,
        "backgroundColor": background,
        "version": chart_js_version,
    }
    if plugins:
        payload["plugins"] = plugins

    http = session or requests.Session()
    try:
        response = http.post(
            "https://quickchart.io/chart/create",
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        body = response.json()
        short_url = body.get("url") or body.get("shortUrl")
        if isinstance(short_url, str) and short_url:
            return short_url
    except requests.RequestException:
        pass

    return long_url


def generate_sankey_chart_config(data: dict, threshold: float = 10.0) -> dict:
    """
    Generates a Chart.js Sankey configuration for QuickChart.
    Links with a value below the threshold are filtered out.
    """

    flows = [
        {
            "from": link["source"],
            "to": link["target"],
            "flow": link["value"],
        }
        for link in data["links"]
        if link["value"] >= threshold
    ]

    if not flows:
        raise ValueError("No Sankey flows remain after applying the threshold filter.")

    chart_title = "UK Energy Flow (Threshold ≥ {threshold})".format(threshold=threshold)

    labels_config = {node["name"]: node["name"] for node in data["nodes"]}

    return {
        "type": "sankey",
        "data": {
            "datasets": [
                {
                    "label": chart_title,
                    "data": flows,
                    "labels": labels_config,
                    "nodeWidth": 26,
                    "nodePadding": 16
                }
            ]
        },
        "options": {
            "plugins": {
                "legend": {
                    "display": False
                },
                "title": {
                    "display": True,
                    "text": chart_title,
                    "color": "#1f2933",
                    "font": {
                        "size": 20,
                        "weight": "600"
                    }
                },
                "tooltip": {
                    "displayColors": False,
                    "backgroundColor": "rgba(15, 23, 42, 0.92)",
                    "titleColor": "#f1f5f9",
                    "bodyColor": "#e2e8f0",
                    "borderColor": "rgba(71, 85, 105, 0.45)",
                    "borderWidth": 1,
                    "padding": 12,
                    "callbacks": {
                        "label": (
                            "function(context) {"
                            "const item = context.dataset.data[context.dataIndex];"
                            "const value = (Math.round(item.flow * 100) / 100).toLocaleString();"
                            "return `${item.from} → ${item.to}: ${value}`;"
                            "}"
                        )
                    }
                }
            },
            "layout": {
                "padding": {
                    "top": 24,
                    "right": 32,
                    "bottom": 16,
                    "left": 32
                }
            },
            "transitions": {
                "active": {
                    "animation": {
                        "duration": 200
                    }
                }
            }
        }
    }


def main():
    """
    Main function to generate and print the Sankey diagram URL.
    """
    # Source data for the energy flow diagram
    sankey_data = {
        "nodes": [{"name":"Agricultural 'waste'"},{"name":"Bio-conversion"},{"name":"Liquid"},{"name":"Losses"},{"name":"Solid"},{"name":"Gas"},{"name":"Biofuel imports"},{"name":"Biomass imports"},{"name":"Coal imports"},{"name":"Coal"},{"name":"Coal reserves"},{"name":"District heating"},{"name":"Industry"},{"name":"Heating and cooling - commercial"},{"name":"Heating and cooling - homes"},{"name":"Electricity grid"},{"name":"Over generation / exports"},{"name":"H2 conversion"},{"name":"Road transport"},{"name":"Agriculture"},{"name":"Rail transport"},{"name":"Lighting & appliances - commercial"},{"name":"Lighting & appliances - homes"},{"name":"Gas imports"},{"name":"Ngas"},{"name":"Gas reserves"},{"name":"Thermal generation"},{"name":"Geothermal"},{"name":"H2"},{"name":"Hydro"},{"name":"International shipping"},{"name":"Domestic aviation"},{"name":"International aviation"},{"name":"National navigation"},{"name":"Marine algae"},{"name":"Nuclear"},{"name":"Oil imports"},{"name":"Oil"},{"name":"Oil reserves"},{"name":"Other waste"},{"name":"Pumped heat"},{"name":"Solar PV"},{"name":"Solar Thermal"},{"name":"Solar"},{"name":"Tidal"},{"name":"UK land based bioenergy"},{"name":"Wave"},{"name":"Wind"}],
        "links": [{"source":"Agricultural 'waste'","target":"Bio-conversion","value":124.729},{"source":"Bio-conversion","target":"Liquid","value":0.597},{"source":"Bio-conversion","target":"Losses","value":26.862},{"source":"Bio-conversion","target":"Solid","value":280.322},{"source":"Bio-conversion","target":"Gas","value":81.144},{"source":"Biofuel imports","target":"Liquid","value":35},{"source":"Biomass imports","target":"Solid","value":35},{"source":"Coal imports","target":"Coal","value":11.606},{"source":"Coal reserves","target":"Coal","value":63.965},{"source":"Coal","target":"Solid","value":75.571},{"source":"District heating","target":"Industry","value":10.639},{"source":"District heating","target":"Heating and cooling - commercial","value":22.505},{"source":"District heating","target":"Heating and cooling - homes","value":46.184},{"source":"Electricity grid","target":"Over generation / exports","value":104.453},{"source":"Electricity grid","target":"Heating and cooling - homes","value":113.726},{"source":"Electricity grid","target":"H2 conversion","value":27.14},{"source":"Electricity grid","target":"Industry","value":342.165},{"source":"Electricity grid","target":"Road transport","value":37.797},{"source":"Electricity grid","target":"Agriculture","value":4.412},{"source":"Electricity grid","target":"Heating and cooling - commercial","value":40.858},{"source":"Electricity grid","target":"Losses","value":56.691},{"source":"Electricity grid","target":"Rail transport","value":7.863},{"source":"Electricity grid","target":"Lighting & appliances - commercial","value":90.008},{"source":"Electricity grid","target":"Lighting & appliances - homes","value":93.494},{"source":"Gas imports","target":"Ngas","value":40.719},{"source":"Gas reserves","target":"Ngas","value":82.233},{"source":"Gas","target":"Heating and cooling - commercial","value":0.129},{"source":"Gas","target":"Losses","value":1.401},{"source":"Gas","target":"Thermal generation","value":151.891},{"source":"Gas","target":"Agriculture","value":2.096},{"source":"Gas","target":"Industry","value":48.58},{"source":"Geothermal","target":"Electricity grid","value":7.013},{"source":"H2 conversion","target":"H2","value":20.897},{"source":"H2 conversion","target":"Losses","value":6.242},{"source":"H2","target":"Road transport","value":20.897},{"source":"Hydro","target":"Electricity grid","value":6.995},{"source":"Liquid","target":"Industry","value":121.066},{"source":"Liquid","target":"International shipping","value":128.69},{"source":"Liquid","target":"Road transport","value":135.835},{"source":"Liquid","target":"Domestic aviation","value":14.458},{"source":"Liquid","target":"International aviation","value":206.267},{"source":"Liquid","target":"Agriculture","value":3.64},{"source":"Liquid","target":"National navigation","value":33.218},{"source":"Liquid","target":"Rail transport","value":4.413},{"source":"Marine algae","target":"Bio-conversion","value":4.375},{"source":"Ngas","target":"Gas","value":122.952},{"source":"Nuclear","target":"Thermal generation","value":839.978},{"source":"Oil imports","target":"Oil","value":504.287},{"source":"Oil reserves","target":"Oil","value":107.703},{"source":"Oil","target":"Liquid","value":611.99},{"source":"Other waste","target":"Solid","value":56.587},{"source":"Other waste","target":"Bio-conversion","value":77.81},{"source":"Pumped heat","target":"Heating and cooling - homes","value":193.026},{"source":"Pumped heat","target":"Heating and cooling - commercial","value":70.672},{"source":"Solar PV","target":"Electricity grid","value":59.901},{"source":"Solar Thermal","target":"Heating and cooling - homes","value":19.263},{"source":"Solar","target":"Solar Thermal","value":19.263},{"source":"Solar","target":"Solar PV","value":59.901},{"source":"Solid","target":"Agriculture","value":0.882},{"source":"Solid","target":"Thermal generation","value":400.12},{"source":"Solid","target":"Industry","value":46.477},{"source":"Thermal generation","target":"Electricity grid","value":525.531},{"source":"Thermal generation","target":"Losses","value":787.129},{"source":"Thermal generation","target":"District heating","value":79.329},{"source":"Tidal","target":"Electricity grid","value":9.452},{"source":"UK land based bioenergy","target":"Bio-conversion","value":182.01},{"source":"Wave","target":"Electricity grid","value":19.013},{"source":"Wind","target":"Electricity grid","value":289.366}]
    }

    # Generate the Chart.js configuration for the Sankey diagram
    chart_config = generate_sankey_chart_config(sankey_data, threshold=10.0)

    # Create the QuickChart URL using the Chart.js configuration and Sankey plugin
    url = build_quickchart_url(
        chart_config,
        plugins=["chartjs-chart-sankey@3.0.0"],
        chart_js_version=3,
        use_short_url=False
    )
    
    return {"result": url}


# --- Execution ---
if __name__ == "__main__":
    result = main()
    print("--- Standard Sankey Diagram (Chart.js via QuickChart) ---")
    print("The following URL points to a generated SVG/PNG image of the Sankey diagram:")
    print(result["result"])

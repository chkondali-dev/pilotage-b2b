import requests
import pandas as pd
import numpy as np
import argparse
import json
import sys
import os
from datetime import datetime, timedelta
from io import BytesIO
from typing import Optional
from pathlib import Path

GITHUB_RAW = "https://raw.githubusercontent.com/chkondali-dev/pilotage-b2b/main/2025/"

FILES = {
    "vc": "Factures%20ventes%20enregistr%C3%A9es%20VC%20(4).xlsx",
    "vc_edc": "Factures%20ventes%20enregistr%C3%A9es%20VC%20CONVENTION%20EDC.xlsx",
    "conventions_signees": "TDC%20CONVENTION%201.xlsm",
    "code_magasin": "Code%20MAGASIN%20Business%20Central.xlsx",
}

NOMS_INDIVIDUELS = {"AHMED ABIDI", "AMARA MISSAOUI", "BILEL BEN AMMAR", "MED KAIS SMAILI"}


def format_k(x: float) -> str:
    if x >= 1_000_000:
        return f"{x/1_000_000:.2f}M"
    elif x >= 1_000:
        return f"{x/1_000:.1f}k"
    elif x >= 0:
        return f"{x:,.0f}"
    return "0"


def _load_excel(url: str) -> Optional[pd.DataFrame]:
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            df = pd.read_excel(BytesIO(r.content), engine="openpyxl")
            df.columns = df.columns.str.replace("\n", " ").str.strip()
            for col in df.select_dtypes("object").columns:
                df[col] = df[col].astype(str).str.strip()
            return df
    except Exception as e:
        print(f"  [trend_analyzer] Erreur chargement: {e}")
    return None


def load_all_data() -> dict:
    dfs = {}
    for name, fname in FILES.items():
        url = GITHUB_RAW + fname
        df = _load_excel(url)
        if df is not None:
            dfs[name] = df
            print(f"  [trend_analyzer] {name}: {len(df)} lignes")
        else:
            dfs[name] = pd.DataFrame()
    return dfs


class TrendAnalyzer:
    def __init__(self, df_vc: pd.DataFrame, df_edc: pd.DataFrame,
                 conventions: pd.DataFrame, code_magasin: pd.DataFrame):
        self._df_vc = df_vc.copy() if not df_vc.empty else df_vc
        self._df_edc = df_edc.copy() if not df_edc.empty else df_edc
        self._conventions = conventions.copy() if not conventions.empty else conventions
        self._code_magasin = code_magasin.copy() if not code_magasin.empty else code_magasin
        self._current_month = datetime.now().month
        self._current_year = datetime.now().year

    def _add_date_cols(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        date_col = next(
            (c for c in df.columns if "date" in c.lower() and "comptabil" in c.lower()), None)
        if date_col is None:
            date_col = next((c for c in df.columns if "date" in c.lower()), None)
        if date_col is None:
            return df
        df = df.copy()
        df["Date"] = pd.to_datetime(df[date_col], errors="coerce")
        df["Annee"] = df["Date"].dt.year.astype("Int64")
        df["Mois"] = df["Date"].dt.month.astype("Int64")
        df["Jour"] = df["Date"].dt.day.astype("Int64")
        return df

    def _filter_conventions(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or "Nom" not in df.columns:
            return df
        return df[~df["Nom"].str.upper().str.strip().isin(NOMS_INDIVIDUELS)].copy()

    def _map_magasins(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or self._code_magasin.empty:
            return df
        df = df.copy()
        df["Enseigne"] = "MG"
        df["Magasin"] = "Inconnu"
        code_col_src = next((c for c in df.columns if c.lower() == "unite code"), None)
        if not code_col_src:
            return df
        code_col = list(self._code_magasin.columns)[0]
        unite_col = list(self._code_magasin.columns)[2] if len(self._code_magasin.columns) > 2 else list(self._code_magasin.columns)[1]

        def get_ense(unit: str) -> str:
            s = str(unit).upper()
            return "BATAM" if ("BATAM" in s or "BTM" in s) else "MG"

        cm = self._code_magasin.copy()
        cm.columns = cm.columns.str.strip()
        cm["Enseigne"] = cm[unite_col].apply(get_ense)
        cm[code_col] = cm[code_col].astype(str).str.strip()
        mapping_nom = cm.set_index(code_col)[unite_col].to_dict()
        mapping_ense = cm.set_index(code_col)["Enseigne"].to_dict()
        df[code_col_src] = df[code_col_src].astype(str).str.strip()
        df["Magasin"] = df[code_col_src].map(mapping_nom).fillna(df[code_col_src])
        df["Enseigne"] = df[code_col_src].map(mapping_ense).fillna("MG")
        return df

    def _ca_for_period(self, df: pd.DataFrame, annee: int, mois: int) -> float:
        if df.empty or "Montant TTC" not in df.columns:
            return 0.0
        d = df[(df["Annee"] == annee) & (df["Mois"] == mois)]
        return float(d["Montant TTC"].sum())

    def _count_for_period(self, df: pd.DataFrame, annee: int, mois: int) -> int:
        if df.empty:
            return 0
        return int(len(df[(df["Annee"] == annee) & (df["Mois"] == mois)]))

    def _compute_entity_trends(self, df: pd.DataFrame, group_col: str, name_col: str = "Magasin") -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame()
        df = df.copy()
        col_lookup = {c.lower(): c for c in df.columns}
        gc = col_lookup.get(group_col.lower())
        if gc is None:
            return pd.DataFrame()
        group_col = gc
        df = self._add_date_cols(df)
        df = self._map_magasins(df)
        entities = df[group_col].unique()
        rows = []
        for entity in entities:
            edf = df[df[group_col] == entity]
            enseigne = edf["Enseigne"].iloc[0] if "Enseigne" in edf.columns else "MG"
            ca_current = self._ca_for_period(edf, self._current_year, self._current_month)
            ca_n1 = self._ca_for_period(edf, self._current_year - 1, self._current_month)
            prev_month = self._current_month - 1
            prev_year = self._current_year
            if prev_month < 1:
                prev_month += 12
                prev_year -= 1
            ca_prev = self._ca_for_period(edf, prev_year, prev_month)
            ca_3m = []
            ca_6m = []
            for i in range(6):
                m = self._current_month - i
                y = self._current_year
                while m < 1:
                    m += 12
                    y -= 1
                val = self._ca_for_period(edf, y, m)
                if i < 3:
                    ca_3m.append(val)
                ca_6m.append(val)
            rolling_3m = float(np.mean(ca_3m)) if ca_3m else 0.0
            rolling_6m = float(np.mean(ca_6m)) if ca_6m else 0.0
            consecutive = 0
            for i in range(6):
                m = self._current_month - i
                y = self._current_year
                while m < 1:
                    m += 12
                    y -= 1
                ca_n = self._ca_for_period(edf, y, m)
                ca_n_1 = self._ca_for_period(edf, y - 1, m)
                if ca_n_1 > 0 and ca_n < ca_n_1:
                    consecutive += 1
                else:
                    break
            yoy_pct = 0.0
            if ca_n1 > 0:
                yoy_pct = round((ca_current - ca_n1) / ca_n1 * 100, 1)
            mom_pct = 0.0
            if ca_prev > 0:
                mom_pct = round((ca_current - ca_prev) / ca_prev * 100, 1)
            tx_current = self._count_for_period(edf, self._current_year, self._current_month)
            tx_n1 = self._count_for_period(edf, self._current_year - 1, self._current_month)
            tx_yoy_pct = 0.0
            if tx_n1 > 0:
                tx_yoy_pct = round((tx_current - tx_n1) / tx_n1 * 100, 1)
            rows.append({
                name_col: edf[name_col].iloc[0] if name_col in edf.columns else entity,
                "Enseigne": enseigne,
                "ca_current_month": ca_current,
                "ca_same_month_last_year": ca_n1,
                "ca_previous_month": ca_prev,
                "yoy_change_pct": yoy_pct,
                "mom_change_pct": mom_pct,
                "rolling_3m_avg": round(rolling_3m, 2),
                "rolling_6m_avg": round(rolling_6m, 2),
                "consecutive_decline_months": consecutive,
                "transaction_count_current": tx_current,
                "transaction_count_last_year": tx_n1,
                "transaction_count_yoy_change_pct": tx_yoy_pct,
            })
        result = pd.DataFrame(rows)
        if not result.empty:
            result = result.sort_values("ca_current_month", ascending=False).reset_index(drop=True)
        return result

    def compute_magasin_trends(self) -> pd.DataFrame:
        return self._compute_entity_trends(self._df_vc, "Unite code", "Magasin")

    def compute_convention_trends(self) -> pd.DataFrame:
        df = self._filter_conventions(self._df_vc)
        return self._compute_entity_trends(df, "Nom", "Nom")

    def apply_rules(self, row) -> list:
        rules = []
        if row["yoy_change_pct"] < -10:
            rules.append({
                "rule_id": "YOY_DROP_10", "severity": "RED",
                "message_fr": f"CA en baisse de {abs(row['yoy_change_pct']):.1f}% vs N-1 ({int(row['ca_same_month_last_year'])} TND vs {int(row['ca_current_month'])} TND)",
                "metric_current": row["ca_current_month"], "metric_previous": row["ca_same_month_last_year"], "threshold": 10.0,
            })
        elif row["yoy_change_pct"] < -5:
            rules.append({
                "rule_id": "YOY_DROP_5", "severity": "AMBER",
                "message_fr": f"CA en baisse de {abs(row['yoy_change_pct']):.1f}% vs N-1 ({int(row['ca_same_month_last_year'])} TND vs {int(row['ca_current_month'])} TND)",
                "metric_current": row["ca_current_month"], "metric_previous": row["ca_same_month_last_year"], "threshold": 5.0,
            })
        if row["consecutive_decline_months"] >= 3:
            rules.append({
                "rule_id": "CONSECUTIVE_3", "severity": "RED",
                "message_fr": f"{int(row['consecutive_decline_months'])} mois consecutifs de baisse vs N-1",
                "metric_current": float(row["consecutive_decline_months"]), "metric_previous": 0, "threshold": 3,
            })
        if row["rolling_3m_avg"] > 0 and row["ca_current_month"] < row["rolling_3m_avg"] * 0.8:
            rules.append({
                "rule_id": "ROLLING_AVG_DROP", "severity": "AMBER",
                "message_fr": f"CA ({int(row['ca_current_month'])} TND) < 80% moyenne 3 mois ({int(row['rolling_3m_avg'])} TND)",
                "metric_current": row["ca_current_month"], "metric_previous": row["rolling_3m_avg"], "threshold": 0.8,
            })
        if row["transaction_count_yoy_change_pct"] < -30:
            rules.append({
                "rule_id": "VOLUME_DROP", "severity": "AMBER",
                "message_fr": f"Transactions en baisse de {abs(row['transaction_count_yoy_change_pct']):.1f}% ({int(row['transaction_count_last_year'])} vs {int(row['transaction_count_current'])})",
                "metric_current": float(row["transaction_count_current"]), "metric_previous": float(row["transaction_count_last_year"]), "threshold": 30.0,
            })
        return rules

    def detect_regressions(self, df_trends: pd.DataFrame) -> pd.DataFrame:
        if df_trends.empty:
            return df_trends
        df = df_trends.copy()

        def compute_severity(row):
            rules = self.apply_rules(row)
            if any(r["severity"] == "RED" for r in rules):
                return "RED", rules
            if rules:
                return "AMBER", rules
            return "GREEN", []

        df[["severity", "triggered_rules"]] = df.apply(
            lambda r: pd.Series(compute_severity(r)), axis=1)
        return df

    def detect_inactivity(self, days: int = 60) -> pd.DataFrame:
        if self._df_vc.empty:
            return pd.DataFrame()
        df = self._add_date_cols(self._map_magasins(self._df_vc))
        today = pd.Timestamp.today().normalize()
        if "Date" not in df.columns:
            return pd.DataFrame()
        last = df.groupby("Magasin").agg(derniere_vente=("Date", "max")).reset_index()
        last["jours_inactivite"] = (today - last["derniere_vente"]).dt.days
        inactive = last[last["jours_inactivite"] > days].copy()
        inactive = inactive.sort_values("jours_inactivite", ascending=False)
        if "Enseigne" in df.columns:
            enseigne_map = df.groupby("Magasin")["Enseigne"].first().to_dict()
            inactive["Enseigne"] = inactive["Magasin"].map(enseigne_map).fillna("MG")
        else:
            inactive["Enseigne"] = "MG"
        return inactive

    def _entity_alerts(self, df_trends: pd.DataFrame, name_col: str, type_label: str) -> list:
        if df_trends.empty:
            return []
        df = self.detect_regressions(df_trends)
        alerts = []
        for _, row in df.iterrows():
            if row["severity"] == "GREEN" and not row.get("triggered_rules", []):
                continue
            alerts.append({
                type_label: row[name_col],
                "enseigne": row.get("Enseigne", "MG"),
                "severity": row["severity"],
                "rules_triggered": row.get("triggered_rules", []),
                "metrics": {
                    "ca_current_month": float(row["ca_current_month"]),
                    "ca_same_month_last_year": float(row["ca_same_month_last_year"]),
                    "yoy_change_pct": float(row["yoy_change_pct"]),
                    "mom_change_pct": float(row["mom_change_pct"]),
                    "rolling_3m_avg": float(row["rolling_3m_avg"]),
                    "consecutive_decline_months": int(row["consecutive_decline_months"]),
                    "transaction_count_current": int(row["transaction_count_current"]),
                    "transaction_count_yoy_change_pct": float(row["transaction_count_yoy_change_pct"]),
                },
            })
        return alerts

    def scan_all(self) -> dict:
        magasin_trends = self.compute_magasin_trends()
        convention_trends = self.compute_convention_trends()
        inactivity = self.detect_inactivity()
        magasin_alerts = self._entity_alerts(magasin_trends, "Magasin", "magasin")
        convention_alerts = self._entity_alerts(convention_trends, "Nom", "nom")
        inactivity_list = []
        if not inactivity.empty:
            for _, row in inactivity.iterrows():
                inactivity_list.append({
                    "entity": row["Magasin"], "type": "magasin",
                    "enseigne": row.get("Enseigne", "MG"),
                    "days_since_last_sale": int(row["jours_inactivite"]),
                    "last_sale_date": str(row["derniere_vente"].date()),
                })
        all_alerts = magasin_alerts + convention_alerts
        red_count = sum(1 for a in all_alerts if a["severity"] == "RED")
        amber_count = sum(1 for a in all_alerts if a["severity"] == "AMBER")
        return {
            "generated_at": datetime.now().isoformat(),
            "scan_version": "1.0",
            "summary": {
                "total_alerts": len(all_alerts),
                "red_alerts": red_count,
                "amber_alerts": amber_count,
                "total_magasins_analyzed": len(magasin_trends) if not magasin_trends.empty else 0,
                "total_conventions_analyzed": len(convention_trends) if not convention_trends.empty else 0,
                "inactive_count": len(inactivity_list),
            },
            "magasin_alerts": magasin_alerts,
            "convention_alerts": convention_alerts,
            "inactivity": inactivity_list,
        }


def save_alerts(path: str, data: dict):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)


def load_alerts(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_summary(data: dict) -> str:
    s = data["summary"]
    lines = [
        f"Scan - {data['generated_at']}",
        f"  Alertes: {s['total_alerts']} ({s['red_alerts']}R, {s['amber_alerts']}A)",
        f"  Magasins: {s['total_magasins_analyzed']} | Conventions: {s['total_conventions_analyzed']}",
        f"  Inactifs: {s['inactive_count']}",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Trend Analysis Agent")
    parser.add_argument("--mode", choices=["scan", "report"], default="scan")
    parser.add_argument("--output", default="data/trend_alerts.json")
    parser.add_argument("--days", type=int, default=60)
    args = parser.parse_args()
    print("[trend_analyzer] Loading data...")
    dfs = load_all_data()
    print("[trend_analyzer] Analyzing trends...")
    ta = TrendAnalyzer(
        df_vc=dfs.get("vc", pd.DataFrame()),
        df_edc=dfs.get("vc_edc", pd.DataFrame()),
        conventions=dfs.get("conventions_signees", pd.DataFrame()),
        code_magasin=dfs.get("code_magasin", pd.DataFrame()),
    )
    result = ta.scan_all()
    if args.mode == "scan":
        save_alerts(args.output, result)
        print(f"[trend_analyzer] Saved: {args.output}")
    print(generate_summary(result))

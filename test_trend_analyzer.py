"""Tests for trend_analyzer.py -- using synthetic data, no external deps."""
import sys, os, json, pytest
sys.path.insert(0,os.path.dirname(__file__))
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from trend_analyzer import TrendAnalyzer, save_alerts, load_alerts, format_k, generate_summary

TODAY = datetime.now()
CY = TODAY.year
CM = TODAY.month

def _make_vc(rows=50):
    np.random.seed(42)
    data=[]
    for i in range(rows):
        code=100+(i%10)
        m=(CM-(i%12))
        y=CY if m<=CM else CY-1
        if m<1: m+=12; y-=1
        data.append({"Unite Code":code,"Montant TTC":np.random.uniform(1000,50000),"Date":f"{y}-{m:02d}-15","Nom":f"CLIENT {chr(65+i%5)}"})
    df=pd.DataFrame(data)
    df["Date"]=pd.to_datetime(df["Date"])
    return df

def _make_code_mag():
    return pd.DataFrame({"Code":[100,101,102,103,104,105,106,107,108,109],"Nom Magasin":[f"MAGASIN {i}" for i in range(10)],"Enseigne":["MG"]*10})

def _make_conv():
    return pd.DataFrame({"Nom":[f"CLIENT {chr(65+i)}" for i in range(5)],"Type":["convention"]*5})

def _make_edc(rows=10):
    return pd.DataFrame({"Unite Code":[100+i for i in range(rows%5+1)],"Montant TTC":np.random.uniform(500,10000,rows%5+1)})

@pytest.fixture
def ta():
    return TrendAnalyzer(df_vc=_make_vc(),df_edc=_make_edc(),conventions=_make_conv(),code_magasin=_make_code_mag())

@pytest.fixture
def ta_empty():
    return TrendAnalyzer(df_vc=pd.DataFrame(),df_edc=pd.DataFrame(),conventions=pd.DataFrame(),code_magasin=pd.DataFrame())
def test_imports(ta):
    assert ta is not None
    assert ta._df_vc is not None

def test_compute_magasin_trends_shape(ta):
    result=ta.compute_magasin_trends()
    assert not result.empty
    expected=["Magasin","ca_current_month","ca_same_month_last_year","yoy_change_pct","mom_change_pct","rolling_3m_avg","consecutive_decline_months","transaction_count_current"]
    for c in expected:
        assert c in result.columns,f"Missing column: {c}"

def test_compute_convention_trends_shape(ta):
    result=ta.compute_convention_trends()
    assert not result.empty
    expected=["Nom","ca_current_month","yoy_change_pct"]
    for c in expected:
        assert c in result.columns,f"Missing column: {c}"

def test_detect_regressions_red(ta):
    trends=ta.compute_magasin_trends()
    trends["yoy_change_pct"]=-15.0
    flagged=ta.detect_regressions(trends)
    red=flagged[flagged["severity"]=="RED"]
    assert len(red)>0,"Should flag RED for -15% YoY"

def test_detect_regressions_amber(ta):
    trends=ta.compute_magasin_trends()
    trends["yoy_change_pct"]=-7.0
    trends["consecutive_decline_months"]=0
    trends["rolling_3m_avg"]=trends["ca_current_month"]*2
    trends["transaction_count_yoy_change_pct"]=0.0
    flagged=ta.detect_regressions(trends)
    amber=flagged[flagged["severity"]=="AMBER"]
    assert len(amber)>0,"Should flag AMBER for -7% YoY"

def test_detect_regressions_green(ta):
    trends=ta.compute_magasin_trends()
    trends["yoy_change_pct"]=5.0
    trends["consecutive_decline_months"]=0
    trends["rolling_3m_avg"]=0
    trends["transaction_count_yoy_change_pct"]=0.0
    flagged=ta.detect_regressions(trends)
    green=flagged[flagged["severity"]=="GREEN"]
    assert len(green)>0,"Should be GREEN for positive YoY"
def test_detect_inactivity(ta):
    result=ta.detect_inactivity(days=0)
    assert not result.empty,"Should detect inactive with 0 day threshold"

def test_scan_all_structure(ta):
    result=ta.scan_all()
    assert "generated_at" in result
    assert "summary" in result
    assert "magasin_alerts" in result
    assert "convention_alerts" in result
    assert "inactivity" in result
    s=result["summary"]
    assert "total_alerts" in s
    assert "red_alerts" in s
    assert "amber_alerts" in s

def test_empty_data(ta_empty):
    result=ta_empty.scan_all()
    assert result["summary"]["total_alerts"]==0
    assert result["summary"]["total_magasins_analyzed"]==0
    assert result["summary"]["total_conventions_analyzed"]==0
    assert len(result["magasin_alerts"])==0

def test_save_load_roundtrip(tmp_path):
    data={"generated_at":"2026-01-01","summary":{"total_alerts":5,"red_alerts":2,"amber_alerts":3,"total_magasins_analyzed":50,"total_conventions_analyzed":60,"inactive_count":1},"magasin_alerts":[{"magasin":"TEST","severity":"RED","enseigne":"MG","rules_triggered":[{"rule_id":"YOY_DROP_10","severity":"RED","message_fr":"Test","metric_current":100,"metric_previous":200,"threshold":10}],"metrics":{}}],"convention_alerts":[],"inactivity":[]}
    p=tmp_path/"test.json"
    save_alerts(str(p),data)
    assert p.exists()
    loaded=load_alerts(str(p))
    assert loaded["summary"]["total_alerts"]==5
    assert loaded["magasin_alerts"][0]["magasin"]=="TEST"

def test_format_k():
    assert format_k(1500)=="1.5k"
    assert format_k(2000000)=="2.00M"
    assert format_k(500)=="500"
    assert format_k(0)=="0"

def test_generate_summary():
    data={"generated_at":"2026-07-24T12:00:00","summary":{"total_alerts":10,"red_alerts":3,"amber_alerts":7,"total_magasins_analyzed":20,"total_conventions_analyzed":30,"inactive_count":2}}
    s=generate_summary(data)
    assert "10" in s
    assert "3" in s
    assert "20" in s

def test_cli_help():
    import subprocess
    r=subprocess.run([sys.executable,"trend_analyzer.py","--help"],capture_output=True,text=True)
    assert r.returncode==0
    assert "mode" in r.stdout

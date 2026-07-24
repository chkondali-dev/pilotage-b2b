"""trend_narrative.py — LLM narrative for regression alerts."""
import os, requests, json, re, sys
from datetime import datetime

LLM_API_KEY = os.getenv("LLM_API_KEY","")
LLM_MODEL = os.getenv("LLM_MODEL","llama-3.3-70b-versatile")
LLM_ENDPOINT = os.getenv("LLM_ENDPOINT","https://api.groq.com/openai/v1/chat/completions")

def call_llm(prompt, api_key=None):
    key = api_key or LLM_API_KEY
    if not key:
        print("Pas de cle API LLM")
        return None
    hdrs = {"Authorization":f"Bearer {key}","Content-Type":"application/json"}
    payload = {"model":LLM_MODEL,"messages":[{"role":"system","content":"Tu es un analyste commercial senior. Reponds en JSON."},{"role":"user","content":prompt}],"temperature":0.3,"max_tokens":8000,"response_format":{"type":"json_object"}}
    try:
        r = requests.post(LLM_ENDPOINT,headers=hdrs,json=payload,timeout=120)
        r.raise_for_status()
        c = r.json()["choices"][0]["message"]["content"]
        c = re.sub(r"^```(?:json)?\s*","",c.strip())
        c = re.sub(r"\s*```$","",c)
        return c
    except Exception as e:
        print(f"LLM: {e}")
        return None

def generate_regression_analysis(alerts):
    summary=alerts.get("summary",{})
    all_alerts=alerts.get("magasin_alerts",[])+alerts.get("convention_alerts",[])
    all_alerts.sort(key=lambda a: (0 if a["severity"]=="RED" else 1))
    top5=all_alerts[:5]
    if not top5:
        return {"synthese":"Aucune regression detectee.","regressions":[],"priorites":[],"generated_at":datetime.now().isoformat()}
    ad=[]
    for a in top5:
        et="magasin" if "magasin" in a else "convention"
        nm=a.get("magasin",a.get("nom","?"))
        rules=[r["rule_id"]+": "+r["message_fr"] for r in a.get("rules_triggered",[])]
        m=a.get("metrics",{})
        ad.append({"nom":nm,"type":et,"enseigne":a.get("enseigne","MG"),"severite":a["severity"],"regles":rules,"ca_actuel":m.get("ca_current_month",0),"variation_pct":m.get("yoy_change_pct",0)})
    s=summary
    prompt="Analyse les 5 principales regressions pour SMG.\nSynthese: "+str(s.get("total_alerts",0))+" alertes ("+str(s.get("red_alerts",0))+"R, "+str(s.get("amber_alerts",0))+"A)."+"\nMagasins: "+str(s.get("total_magasins_analyzed",0))+" \x7c Conventions: "+str(s.get("total_conventions_analyzed",0))+" \x7c Inactifs: "+str(s.get("inactive_count",0))+"\n\nTop regressions:\n"+json.dumps(ad,ensure_ascii=False,indent=2)+"\n\nReponds JSON avec: synthese, regressions (nom, analyse, recommandation), priorites (action, urgence)."
    resp=call_llm(prompt)
    if resp:
        try:
            return json.loads(resp)
        except:
            pass
    r=s.get("red_alerts",0)
    a=s.get("amber_alerts",0)
    return {"synthese":"Scan auto: "+str(r)+"R, "+str(a)+"A. LLM indisponible.","regressions":[],"priorites":[{"action":"Investiguer alertes ROUGES","urgence":"haute"}],"generated_at":datetime.now().isoformat()}

if __name__=="__main__":
    ip=sys.argv[1] if len(sys.argv)>1 else "data/trend_alerts.json"
    op=sys.argv[2] if len(sys.argv)>2 else "data/trend_narrative.json"
    with open(ip,"r",encoding="utf-8") as fh:
        alerts=json.load(fh)
    result=generate_regression_analysis(alerts)
    with open(op,"w",encoding="utf-8") as fh:
        json.dump(result,fh,ensure_ascii=False,indent=2)
    print("Narrative saved:",op)

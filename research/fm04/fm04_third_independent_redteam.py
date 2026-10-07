from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import subprocess
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path
from statistics import mean
from contextlib import redirect_stdout

ROOT=Path("research")
TZ8=timezone(timedelta(hours=8))
MODELS=("SEASONAL_NAIVE","PERSISTENCE_YOY","TREND_LOG_LINEAR_8Q","MEAN_REVERSION_YOY_8")
HORIZONS={"3M":1,"6M":2,"12M":4}
STATES=("DIRECTION","MOMENTUM","VOLATILITY","SEASONALITY","MEAN_REVERSION_PRESSURE","STRUCTURAL_STABILITY","DATA_QUALITY")

def qkey(p): return int(p[:4]), int(p[5])
def qadd(p,o):
    y,q=qkey(p); serial=y*4+q-1+o; return f"{serial//4}Q{serial%4+1}"
def qcutoff(p):
    y,q=qkey(p); m={1:3,2:6,3:9,4:12}[q]; d={1:31,2:30,3:30,4:31}[q]
    return datetime(y,m,d,23,59,59,tzinfo=TZ8)
def dt(v):
    x=datetime.fromisoformat(v)
    assert x.tzinfo is not None
    return x
def csha(v):
    return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def blob(path):
    return subprocess.check_output(["git","hash-object",str(path)],text=True).strip()
def load_json(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def load_ndjson(p): return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]

def visible(by_period,origin):
    cutoff=qcutoff(origin); out={}
    for period, rows in by_period.items():
        candidates=[r for r in rows if dt(r["known_at"])<=cutoff]
        assert len(candidates)<=1, "AMBIGUOUS_VISIBLE_REVISION"
        if candidates: out[period]=candidates[0]
    return out

def req(vis,p):
    if p not in vis: raise LookupError(p)
    return vis[p]

def ref_forecast(model,by_period,origin,horizon):
    h=HORIZONS[horizon]; target=qadd(origin,h); base=qadd(target,-4); vis=visible(by_period,origin)
    if model=="SEASONAL_NAIVE": return float(req(vis,base)["value"]),[req(vis,base)["record_id"]]
    if model=="PERSISTENCE_YOY":
        cur=req(vis,origin); prev=req(vis,qadd(origin,-4)); b=req(vis,base)
        yoy=float(cur["value"])/float(prev["value"])-1.0
        return float(b["value"])*(1.0+yoy),[b["record_id"],cur["record_id"],prev["record_id"]]
    if model=="TREND_LOG_LINEAR_8Q":
        pts=[]; ids=[]
        for i in range(8):
            r=req(vis,qadd(origin,-7+i)); v=float(r["value"]); assert v>0; pts.append((i,math.log(v))); ids.append(r["record_id"])
        xb=3.5; yb=mean(y for _,y in pts); denom=sum((i-xb)**2 for i,_ in pts)
        slope=sum((i-xb)*(y-yb) for i,y in pts)/denom; intercept=yb-slope*xb
        return math.exp(intercept+slope*(7+h)),ids
    if model=="MEAN_REVERSION_YOY_8":
        b=req(vis,base); growths=[]; ids=[b["record_id"]]
        for offset in range(-7,1):
            cur=req(vis,qadd(origin,offset)); prev=req(vis,qadd(origin,offset-4))
            pv=float(prev["value"]); assert pv!=0; growths.append(float(cur["value"])/pv-1.0); ids.extend([cur["record_id"],prev["record_id"]])
        return float(b["value"])*(1.0+mean(growths)),sorted(set(ids))
    raise AssertionError("UNKNOWN_MODEL")

def metric(pred,actual):
    e=abs(pred-actual); denom=abs(pred)+abs(actual)
    return {"MAE":e,"RMSE":e,"sMAPE":0.0 if denom==0 else 200.0*e/denom}

def independent_full_check(result,states,records,lock,contract):
    assert result["schema_version"]=="IIOS-FM04-CONDITIONAL-BACKTEST-RESULT-0.2"
    assert result["confirmatory_eligible"] is False
    paths={
        "state_contract":"research/fm03/FM03_STATE_CONTRACT.json",
        "driver_history":"research/fm01/CATL_DRIVER_HISTORY.ndjson",
        "outer_universe_lock":"research/fm00/OU-M12-FM00-CATL-001.json",
        "research_plan":"research/fm00/RP-M12-FM00-EXP-001.json",
        "candidate_space":"research/fm00/CS-M12-FM00-CATL-001.json",
        "purity_boundary":"research/fm00/EPB-M12-FM00-EXP-001.json",
    }
    expected_blobs=contract["input_contract"]["upstream_git_blob_sha"]
    for name,path in paths.items():
        assert blob(Path(path))==expected_blobs[name]
        assert result["input_bindings"][name+"_git_blob_sha"]==expected_blobs[name]
    assert result["input_bindings"]["state_snapshot_sha256"]==csha(states)
    assert result["input_bindings"]["driver_history_canonical_sha256"]==csha(records)
    assert result["input_bindings"]["outer_universe_lock_canonical_sha256"]==csha(lock)
    state={(r["origin_id"],r["driver_id"]):r for r in states}
    by={"REVENUE":{},"NET_PROFIT":{}}
    for r in records: by[r["driver_id"]].setdefault(r["period"],[]).append(r)
    for r in result["outer_selection_evaluations"]:
        sr=state[(r["outer_origin_id"],r["driver_id"])]
        st=sr["states"][r["state_dimension"]]
        assert r["state_row_id"]==sr["state_row_id"] and r["state_status"]==st["status"] and r["state_value"]==st.get("state")
        elig=next(x for x in result["selection_eligibility"] if x["selection_id"]==r["selection_id"])
        assert elig["eligible"]==(r["status"] in ("SELECTED","SELECTED_AND_EVALUATED","SELECTED_BUT_OUTER_UNAVAILABLE"))
        assert elig["reason"]==r["no_selection_reason"]
        for obs in r["provenance"]["inner"]:
            inner=obs["inner_origin_id"]; assert qkey(inner)<qkey(r["outer_origin_id"])
            target=qadd(inner,HORIZONS[r["horizon"]]); assert qkey(target)<=qkey(r["outer_origin_id"])
            ar=by[r["driver_id"]][target]; assert len(ar)==1 and obs["inner_actual_record_id"]==ar[0]["record_id"]
            assert dt(ar[0]["known_at"])<=qcutoff(r["outer_origin_id"])
            for m in MODELS:
                pred,ids=ref_forecast(m,by[r["driver_id"]],inner,r["horizon"])
                assert math.isfinite(pred)
                assert obs["inner_model_input_record_ids"][m]==ids
    groups=[]
    for origin_item in lock["origins"]:
        origin=origin_item["origin_id"]
        for h in origin_item["scheduled_horizons"]:
            for d in ("REVENUE","NET_PROFIT"):
                sr=state[(origin,d)]
                for dim in STATES:
                    st=sr["states"][dim]
                    if st["status"]=="AVAILABLE": groups.append((d,h,dim,st["state"]))
    expected_groups=[{"group_id":f"FM04-GRP-{d}-{h}-{dim}-{v}","driver_id":d,"horizon":h,"state_dimension":dim,"state_value":v} for d,h,dim,v in sorted(set(groups))]
    assert result["conditional_group_definitions"]==expected_groups
    assert result["summary"]["conditional_group_count"]==len(expected_groups)
    empirical=result["conditional_empirical_performance"]
    assert result["summary"]["empirical_conditional_group_count"]==len(empirical)
    for e in empirical:
        gd=next(g for g in expected_groups if g["group_id"]==e["group_id"])
        assert all(e[k]==gd[k] for k in ("driver_id","horizon","state_dimension","state_value"))
        assert e["selection_eligible"] is False and e["descriptive_only"] is True
        assert e["common_outer_sample_size"]==len(e["observations"] )==len(e["common_outer_origins"])
        for o in e["observations"]:
            origin=o["outer_origin_id"]; d=e["driver_id"]; h=e["horizon"]
            assert qkey(qadd(origin,HORIZONS[h]))>=qkey(origin)
            ar=by[d][qadd(origin,HORIZONS[h])]; assert len(ar)==1 and o["actual_record_id"]==ar[0]["record_id"]
            for m in MODELS:
                pred,ids=ref_forecast(m,by[d],origin,h); mm=metric(pred,float(ar[0]["value"]))
                assert o["model_input_record_ids"][m]==ids
                assert math.isclose(o["model_forecasts"][m],pred,rel_tol=0,abs_tol=1e-12)
                assert all(math.isclose(o["model_metrics"][m][k],mm[k],rel_tol=0,abs_tol=1e-12) for k in mm)

def mutate_and_expect_reject(base_result,state_path,mutate,label):
    import sys
    sys.path.insert(0, "research/fm04")
    import fm04_independent_audit as module
    value=copy.deepcopy(base_result); mutate(value)
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/(label+".json"); p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        old=os.environ.get("FM04_BACKTEST_RESULT")
        try:
            os.environ["FM04_BACKTEST_RESULT"]=str(p)
            with redirect_stdout(StringIO()):
                try: module.main(); accepted=True
                except Exception: accepted=False
        finally:
            if old is None: os.environ.pop("FM04_BACKTEST_RESULT",None)
            else: os.environ["FM04_BACKTEST_RESULT"]=old
    assert not accepted, "MUTATION_ACCEPTED:"+label

def main():
    import sys
    sys.path.insert(0,"research/fm04")
    from fm04_conditional_backtest import build_result
    contract=load_json(ROOT/"fm04/FM04_CONDITIONAL_BACKTEST_CONTRACT.json")
    states=load_ndjson(Path(os.environ["FM03_STATE_SNAPSHOT"]))
    records=load_ndjson(ROOT/"fm01/CATL_DRIVER_HISTORY.ndjson")
    lock=load_json(ROOT/"fm00/OU-M12-FM00-CATL-001.json")
    result=build_result(contract,states,lock,records)
    independent_full_check(result,states,records,lock,contract)

    import importlib.util
    spec=importlib.util.spec_from_file_location("fm04_audit","research/fm04/fm04_independent_audit.py")
    audit=importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)
    with tempfile.TemporaryDirectory() as td:
        base=Path(td)/"baseline.json"; base.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        os.environ["FM04_BACKTEST_RESULT"]=str(base); os.environ["FM03_STATE_SNAPSHOT"]=os.environ["FM03_STATE_SNAPSHOT"]
        with redirect_stdout(StringIO()): audit.main()
        def add_attack(label, mutation):
            mutated=copy.deepcopy(result)
            mutation(mutated)
            p=Path(td)/(label+".json")
            p.write_text(json.dumps(mutated,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            os.environ["FM04_BACKTEST_RESULT"]=str(p)
            accepted=True
            try:
                with redirect_stdout(StringIO()): audit.main()
            except Exception:
                accepted=False
            assert not accepted, label

        def mut_empirical_metric(x):
            if x["conditional_empirical_performance"]:
                x["conditional_empirical_performance"][0]["models"][MODELS[0]]["metrics"]["MAE"] += 1.0

        def mut_empirical_actual(x):
            if x["conditional_empirical_performance"]:
                x["conditional_empirical_performance"][0]["observations"][0]["actual_record_id"] = "FORGED"

        attacks=[
            ("mutate_empirical_metric",mut_empirical_metric),
            ("mutate_empirical_observation_actual",mut_empirical_actual),
            ("mutate_group_definition",lambda x: x["conditional_group_definitions"][0].__setitem__("state_value","FORGED")),
            ("mutate_selection_eligibility",lambda x: x["selection_eligibility"][0].__setitem__("eligible",True)),
            ("mutate_all_driver_binding",lambda x: x["input_bindings"].__setitem__("driver_history_git_blob_sha","0"*40)),
            ("mutate_all_plan_binding",lambda x: x["input_bindings"].__setitem__("research_plan_git_blob_sha","0"*40)),
            ("mutate_summary_count",lambda x: x["summary"].__setitem__("no_selection_count",0)),
        ]
        for label,mutation in attacks:
            add_attack(label, mutation)
            os.environ["FM04_BACKTEST_RESULT"]=str(p)
            accepted=True
            try:
                with redirect_stdout(StringIO()): audit.main()
            except Exception: accepted=False
            assert not accepted, label
    print(json.dumps({"baseline":"PASS","independent_full_result_replay":"PASS","mutation_attacks":"PASS","attack_count":len(attacks)},ensure_ascii=False))

if __name__=="__main__": main()

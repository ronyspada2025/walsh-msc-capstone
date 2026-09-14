"""Strict output integrity and comparison to the final report values."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import pandas as pd

INPUT_SHA='50fac84b16f63d66628741f36686cc076f43c90632a3befe53ca43ed9b316207'
REQUIRED_FILES=[
 'tables/headline_results.json','tables/extended_results.json','tables/model_frame.csv',
 'tables/split_membership.csv','tables/held_out_predictions.csv','tables/repeated_cv_fold_scores.csv',
 'tables/table04_dataset_structure.csv','tables/table05_cleaning_log.csv',
 'tables/table08_descriptives.csv','tables/table09_missingness.csv','tables/table10_speed_by_stage.csv',
 'tables/table11_model_comparison.csv','tables/table12_rq1_performance.csv',
 'tables/table13_state_validation.csv','tables/table14_predictive_performance.csv',
 'tables/table15_truncated_nb.csv','tables/table16_unconditional_nb.csv',
 'tables/table17_cluster_profiles.csv','tables/table18_slp_odds_ratios.csv',
 'tables/table19_screening_metrics.csv','tables/table19_confusion_matrix.csv','tables/table20_slp_sensitivity.csv',
 'tables/tnb_bootstrap_diagnostics.json','tables/logit_bootstrap_diagnostics.json',
 'tables/rq2_ridge_intervals.csv','figures/figure01_conceptual_framework.png',
 'figures/figure10_workflow.png','figures/figure11_permutation_importance.png',
 'figures/figure12_roc_curves.png']


def get_path(obj,path):
    for part in path:
        if isinstance(obj,list): obj=obj[int(part)]
        elif part in obj: obj=obj[part]
        elif part.isdigit() and int(part) in obj: obj=obj[int(part)]
        else: raise KeyError(part)
    return obj


def _finite(obj,path='result'):
    if isinstance(obj,dict):
        for k,v in obj.items(): _finite(v,path+'.'+str(k))
    elif isinstance(obj,list):
        for i,v in enumerate(obj): _finite(v,path+f'[{i}]')
    elif isinstance(obj,float) and not math.isfinite(obj):
        raise ValueError(f'Nonfinite value at {path}')


def verify_results(result,output,root,require_full=True,verify_manifest=True):
    output,root=Path(output),Path(root)
    if not result or result.get('run',{}).get('status')!='complete': raise ValueError('Incomplete result')
    state_file=output/'execution_status.json'
    if verify_manifest and state_file.exists():
        state=json.loads(state_file.read_text())
        if state.get('status')!='complete' or state.get('run_id')!=result.get('run',{}).get('run_id'):
            raise ValueError('The latest execution is incomplete or differs from the published results')
    if require_full and result['run']['mode']!='full': raise ValueError('Diagnostic run is not a full reproduction')
    _finite(result)
    for key,expected in [('clean_rows',5571),('model_n',5564),('exact_duplicate_rows_dropped',193),('duplicate_key_rows',4343)]:
        if result.get(key)!=expected: raise ValueError(f'Invalid {key}')
    actual=hashlib.sha256((root/'data/processed/merged_municipal_dataset.csv').read_bytes()).hexdigest()
    if result.get('input_sha256')!=INPUT_SHA or actual!=INPUT_SHA: raise ValueError('Dataset checksum mismatch')
    if result['run']['packages'].get('scikit-learn')!='1.8.0': raise ValueError('scikit-learn 1.8.0 required')
    for path,sha in result['run']['source_sha256'].items():
        f=root/path
        if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest()!=sha:
            raise ValueError('Source changed since execution: '+path)
    missing=[p for p in REQUIRED_FILES if not (output/p).is_file()]
    if missing: raise ValueError('Missing output files: '+', '.join(missing))
    ext=result['extended']
    if require_full and ext['protocol']['state_bootstrap_resamples']!=999: raise ValueError('999 state resamples required')
    for kind in ['tnb','slp']:
        obj=ext['inference'][kind]; boot=obj['bootstrap']
        if not obj['converged']: raise ValueError(kind+' inference did not converge')
        if boot['valid']<.8*boot['requested']: raise ValueError(kind+' bootstrap reliability gate failed')
        if sum(boot['status_counts'].values())!=boot['requested']: raise ValueError('Missing bootstrap statuses')
    for name in ['count','percap','presence','slp']:
        for seed in ['42','2026']:
            row=ext['predictive'][name][seed]
            if sum(row['confusion'].values())!=row['n_test']: raise ValueError('Invalid confusion matrix total')
            if row['auc_bootstrap']['requested']!=1000: raise ValueError('Expected 1000 metric resamples')
            if not 0<=row['auc']<=1: raise ValueError('Invalid AUC')
        if len(ext['predictive'][name]['repeated_cv']['roc_auc']['fold_scores'])!=25:
            raise ValueError('Expected 25 repeated CV scores')
    frame=pd.read_csv(output/'tables/model_frame.csv',dtype={'MUNICIP_ID':str})
    if len(frame)!=5564 or frame.MUNICIP_ID.duplicated().any(): raise ValueError('Invalid exported modeling frame')
    memberships=pd.read_csv(output/'tables/split_membership.csv',dtype={'MUNICIP_ID':str})
    for (model,seed), sub in memberships.groupby(['model','split_seed']):
        tr=set(sub.loc[sub.partition=='train','MUNICIP_ID']); te=set(sub.loc[sub.partition=='test','MUNICIP_ID'])
        if tr&te or len(tr)!=4173 or len(te)!=1391 or tr|te!=set(frame.MUNICIP_ID):
            raise ValueError(f'Invalid partition {model}/{seed}')
    if verify_manifest:
        manifest=json.loads((output/'run_manifest.json').read_text())
        for path,expected in manifest['files'].items():
            f=output/path
            if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest()!=expected:
                raise ValueError('Output changed since execution: '+path)
        if not set(REQUIRED_FILES).issubset(manifest['files']): raise ValueError('Manifest missing required files')
        recorded=json.loads((output/'report_comparison.json').read_text())
        reference=root/'scripts/final_report_reference.json'
        if recorded.get('reference_sha256')!=hashlib.sha256(reference.read_bytes()).hexdigest():
            raise ValueError('Final report reference changed since execution')
    return True


def compare_report(result,reference_path,output=None):
    fixture=json.loads(Path(reference_path).read_text())
    if not fixture.get('metrics'): raise ValueError('Final report reference has no metrics')
    rows=[]
    for ref in fixture['metrics']:
        row=dict(ref)
        try:
            value=get_path(result,ref['path'])
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
                raise ValueError('Metric is not a finite number')
            row['computed']=value
            places=ref['decimals']
            row['computed_display']=f'{value:.{places}f}'
            if ref.get('operator')=='lt':
                row['status']='MATCH' if value<float(ref['reported']) else 'DIFFERS'
            else:
                row['status']='MATCH' if row['computed_display']==f'{float(ref["reported"]):.{places}f}' else 'DIFFERS'
        except (KeyError,IndexError,TypeError,ValueError) as err:
            row.update(status='MISSING_OR_INVALID',computed=None,error=str(err))
        rows.append(row)
    summary={s:sum(v['status']==s for v in rows) for s in ['MATCH','DIFFERS','MISSING_OR_INVALID']}
    comparison={'reference':fixture['source'],'mode':result.get('run',{}).get('mode'),
                'reference_sha256':hashlib.sha256(Path(reference_path).read_bytes()).hexdigest(),
                'summary':summary,'exact_match':all(v['status']=='MATCH' for v in rows),'metrics':rows}
    if output is not None:
        output=Path(output)
        (output/'report_comparison.json').write_text(json.dumps(comparison,indent=2,allow_nan=False)+'\n')
        lines=['# Final report numerical verification','',
            f'Run mode: **{comparison["mode"]}**. {summary["MATCH"]} matched, {summary["DIFFERS"]} differ, {summary["MISSING_OR_INVALID"]} missing/invalid.','',
            'Computed values are checked against the final report at its displayed precision. The reference file is used for verification only; model estimation is independent of these values.','',
            '| Location | Metric | Report | Computed | Status |','|---|---|---:|---:|---|']
        for row in rows:
            if row['status']!='MATCH': lines.append(f'| {row["location"]} | {row["name"]} | {row["reported"]} | {row.get("computed_display","missing")} | {row["status"]} |')
        lines+=['','All comparisons, including matches, are in `report_comparison.json`.','',
            'A complete match requires every declared metric to be present, finite, and consistent with the report. Any failed check returns a nonzero verification status.']
        (output/'report_comparison.md').write_text('\n'.join(lines)+'\n')
    return comparison

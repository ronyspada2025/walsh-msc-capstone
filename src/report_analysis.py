"""Complete report analyses using the one authoritative cleaned modeling frame.

No reported metric is used to fit a model, choose a seed, or replace an output.
Bootstrap streams are restarted at seed 42 for each statistic and model.
"""
from __future__ import annotations

import json
import warnings
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from joblib import Parallel, delayed
from scipy import stats
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression, RidgeCV
from sklearn.metrics import (accuracy_score, average_precision_score, brier_score_loss,
    confusion_matrix, f1_score, mean_absolute_error, r2_score, recall_score,
    precision_score, roc_auc_score, roc_curve)
from sklearn.model_selection import (GridSearchCV, GroupKFold, RepeatedStratifiedKFold,
    cross_validate, train_test_split)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from statsmodels.discrete.truncated_model import TruncatedLFNegativeBinomialP

RF_GRID = {'n_estimators': [300, 600], 'max_depth': [None, 8, 14], 'min_samples_leaf': [1, 5]}
SEED = 42


def write_json(path, value):
    def convert(x):
        if isinstance(x, np.ndarray): return x.tolist()
        if isinstance(x, np.generic): return x.item()
        raise TypeError(type(x).__name__)
    Path(path).write_text(json.dumps(value, indent=2, default=convert, allow_nan=False) + '\n')


def bootstrap_metric(y, prediction, metric, n=1000):
    """Percentile CI for a fixed fitted model, resampling held-out rows only."""
    y, prediction = np.asarray(y), np.asarray(prediction)
    rng = np.random.RandomState(SEED)
    values = []
    for _ in range(n):
        idx = rng.choice(len(y), len(y), replace=True)
        if metric is roc_auc_score and len(np.unique(y[idx])) != 2: continue
        value = float(metric(y[idx], prediction[idx]))
        if np.isfinite(value): values.append(value)
    if len(values) < .95 * n:
        raise RuntimeError('Too few valid held-out bootstrap replications')
    return {'ci': np.percentile(values, [2.5, 97.5]).tolist(), 'requested': n,
            'valid': len(values), 'seed': SEED, 'method': 'row percentile; fitted model held fixed'}


def summary_cv(result):
    return {name: {'mean': float(result['test_' + name].mean()),
                   'sd': float(result['test_' + name].std()),
                   'min': float(result['test_' + name].min()),
                   'max': float(result['test_' + name].max()),
                   'fold_scores': result['test_' + name].tolist()}
            for name in ['roc_auc', 'f1']}


def predictive(frame, structural, baseline, tab_dir, fig_dir, jobs):
    X = frame[structural].astype(float)
    targets = {'count': frame.HIGH_NR_P75,
               'percap': (frame.NR_PER_100K_POP > frame.NR_PER_100K_POP.quantile(.75)).astype(int),
               'presence': (frame.NR_STATION_CNT > 0).astype(int), 'slp': frame.HIGH_SLP}
    forest = RandomForestClassifier(**baseline['rq1_leakage_free_p75']['best_params'],
                                   class_weight='balanced', random_state=SEED)
    logistic = Pipeline([('scale', StandardScaler()),
        ('clf', LogisticRegression(class_weight='balanced', max_iter=2000, random_state=SEED))])
    tr, te = train_test_split(np.arange(len(frame)), test_size=.25,
                             stratify=targets['percap'], random_state=SEED)
    grid = GridSearchCV(RandomForestClassifier(class_weight='balanced', random_state=SEED),
                        RF_GRID, cv=5, scoring='f1', n_jobs=jobs, error_score='raise')
    grid.fit(X.iloc[tr], targets['percap'].iloc[tr])
    pd.DataFrame(grid.cv_results_).drop(columns='params').to_csv(tab_dir/'rq1_percap_grid.csv', index=False)
    models = {'count': forest, 'percap': grid.best_estimator_, 'presence': logistic, 'slp': logistic}
    result = {'percap_best_params': grid.best_params_}
    predictions, splits, performance, cv_rows, importances, roc = [], [], [], [], {}, {}
    for name, model in models.items():
        print(f'  Predictive validation: {name}', flush=True)
        y = targets[name]
        block = result[name] = {}
        oldtr, _ = train_test_split(np.arange(len(frame)), test_size=.25, stratify=y, random_state=42)
        for seed in [42, 2026]:
            tr, te = train_test_split(np.arange(len(frame)), test_size=.25, stratify=y, random_state=seed)
            fit = clone(model).fit(X.iloc[tr], y.iloc[tr])
            proba, pred = fit.predict_proba(X.iloc[te])[:, 1], fit.predict(X.iloc[te])
            tn, fp, fn, tp = confusion_matrix(y.iloc[te], pred, labels=[0, 1]).ravel()
            prevalence = float(y.iloc[te].mean())
            values = {'auc': float(roc_auc_score(y.iloc[te], proba)),
                'auc_bootstrap': bootstrap_metric(y.iloc[te], proba, roc_auc_score),
                'accuracy': float(accuracy_score(y.iloc[te], pred)), 'f1': float(f1_score(y.iloc[te], pred)),
                'recall': float(recall_score(y.iloc[te], pred)),
                'specificity': float(tn/(tn+fp)), 'precision': float(precision_score(y.iloc[te], pred)),
                'pr_auc': float(average_precision_score(y.iloc[te], proba)),
                'brier': float(brier_score_loss(y.iloc[te], proba)),
                'confusion': {'tp': int(tp), 'fn': int(fn), 'fp': int(fp), 'tn': int(tn)},
                'n_train': len(tr), 'n_test': len(te), 'prevalence': prevalence,
                'majority_accuracy': max(prevalence, 1-prevalence),
                'always_positive_f1': 2*prevalence/(1+prevalence),
                'brier_reference': prevalence*(1-prevalence)}
            block[str(seed)] = values
            performance.append({'model': name, 'split_seed': seed,
                **{k:v for k,v in values.items() if isinstance(v,(int,float))},
                'auc_ci_low': values['auc_bootstrap']['ci'][0], 'auc_ci_high': values['auc_bootstrap']['ci'][1]})
            predictions.extend({'model':name,'split_seed':seed,'MUNICIP_ID':frame.MUNICIP_ID.iloc[i],
                'observed':int(y.iloc[i]),'probability':float(p),'predicted':int(h)} for i,p,h in zip(te,proba,pred))
            for part, idx in [('train',tr),('test',te)]:
                splits.extend({'model':name,'split_seed':seed,'partition':part,'MUNICIP_ID':frame.MUNICIP_ID.iloc[i]} for i in idx)
            if seed == 42:
                cv = cross_validate(model,X.iloc[tr],y.iloc[tr],cv=5,scoring=['roc_auc','f1'],n_jobs=jobs,error_score='raise')
                values['training_cv'] = summary_cv(cv)
                roc[name] = roc_curve(y.iloc[te],proba)[:2]
                if name in ['count','percap']:
                    pi = permutation_importance(fit,X.iloc[te],y.iloc[te],scoring='roc_auc',
                                                 n_repeats=20,random_state=SEED,n_jobs=jobs)
                    values['permutation_importance'] = dict(zip(structural,pi.importances_mean.tolist()))
                    values['permutation_importance_sd'] = dict(zip(structural,pi.importances_std.tolist()))
                    importances[name] = values['permutation_importance']
            else:
                values['test_rows_used_in_seed42_training'] = len(set(oldtr)&set(te))
                values['interpretation'] = 'fresh partition sensitivity; not an untouched model-selection holdout'
        cv = cross_validate(model,X,y,cv=RepeatedStratifiedKFold(n_splits=5,n_repeats=5,random_state=SEED),
                            scoring=['roc_auc','f1'],n_jobs=jobs,error_score='raise')
        block['repeated_cv'] = summary_cv(cv)
        for metric, obj in block['repeated_cv'].items():
            cv_rows.extend({'model':name,'metric':metric,'repeat':i//5+1,'fold':i%5+1,'score':score}
                           for i,score in enumerate(obj['fold_scores']))
        # Main pipeline already computes grouped validation for count and SLP.
        if name == 'presence':
            cv = cross_validate(model,X,y,groups=frame.MUNICIP_ID.str[:2],cv=GroupKFold(5),
                                scoring=['roc_auc','f1'],n_jobs=jobs,error_score='raise')
            block['state_cv'] = summary_cv(cv)
        write_json(tab_dir/'predictive_checkpoint.json',result)
    pd.DataFrame(predictions).to_csv(tab_dir/'held_out_predictions.csv',index=False)
    pd.DataFrame(splits).to_csv(tab_dir/'split_membership.csv',index=False)
    pd.DataFrame(cv_rows).to_csv(tab_dir/'repeated_cv_fold_scores.csv',index=False)
    pd.DataFrame(performance).to_csv(tab_dir/'table14_predictive_performance.csv',index=False)
    pd.DataFrame(importances).to_csv(tab_dir/'figure11_permutation_importance.csv')
    import matplotlib.pyplot as plt
    imp = pd.DataFrame(importances).sort_values('count')
    ax = imp.plot.barh(figsize=(9,6),color=['#17688f','#e98b24'])
    ax.set_xlabel('Mean decrease in held-out ROC-AUC; 20 permutations')
    ax.set_title('RQ1 permutation importance by target definition')
    ax.figure.tight_layout(); ax.figure.savefig(fig_dir/'figure11_permutation_importance.png',dpi=200); plt.close(ax.figure)
    fig,ax=plt.subplots(figsize=(8,6))
    for name in ['count','percap','presence','slp']:
        ax.plot(*roc[name],label=f'{name}: AUC {result[name]["42"]["auc"]:.3f}')
    ax.plot([0,1],[0,1],'k--',label='Chance'); ax.set(xlabel='False positive rate',ylabel='True positive rate',title='Held-out ROC curves, seed 42')
    ax.legend(); fig.tight_layout(); fig.savefig(fig_dir/'figure12_roc_curves.png',dpi=200); plt.close(fig)
    pd.DataFrame([result['slp']['42']['confusion']]).to_csv(tab_dir/'table19_confusion_matrix.csv',index=False)
    pd.DataFrame([v for v in performance if v['model']=='slp' and v['split_seed']==42]).to_csv(tab_dir/'table19_screening_metrics.csv',index=False)
    return result


def ridge_intervals(frame, structural, tab_dir):
    result, predictions = {}, []
    for mode in ['raw','log','conditional_log']:
        sub = frame if mode != 'conditional_log' else frame[frame.NR_STATION_CNT>0]
        X=sub[structural].astype(float)
        y=sub.NR_PER_100K_POP if mode=='raw' else np.log1p(sub.NR_PER_100K_POP)
        tr,te=train_test_split(np.arange(len(sub)),test_size=.25,random_state=42)
        # RidgeCV selects the penalty. Scaling occurs before its inner CV.
        # It is retained for reproduction, not described as perfectly nested preprocessing.
        model=Pipeline([('scale',StandardScaler()),('ridge',RidgeCV(alphas=np.logspace(-2,3,30),cv=5))])
        fit=model.fit(X.iloc[tr],y.iloc[tr]); pred=fit.predict(X.iloc[te])
        result[mode]={'r2':float(r2_score(y.iloc[te],pred)),'mae':float(mean_absolute_error(y.iloc[te],pred)),
            'r2_bootstrap':bootstrap_metric(y.iloc[te],pred,r2_score),'n':len(sub),'n_test':len(te),
            'alpha':float(fit.named_steps['ridge'].alpha_)}
        predictions.extend({'specification':mode,'MUNICIP_ID':sub.MUNICIP_ID.iloc[i],
            'observed':float(obs),'predicted':float(p)} for i,obs,p in zip(te,y.iloc[te],pred))
    pd.DataFrame(predictions).to_csv(tab_dir/'ridge_held_out_predictions.csv',index=False)
    pd.DataFrame([{**v,'specification':k,'r2_ci_low':v['r2_bootstrap']['ci'][0],
        'r2_ci_high':v['r2_bootstrap']['ci'][1]} for k,v in result.items()]).drop(columns='r2_bootstrap').to_csv(tab_dir/'rq2_ridge_intervals.csv',index=False)
    return result


def _make_model(kind,y,X,offset):
    if kind=='tnb': return TruncatedLFNegativeBinomialP(y,X,offset=offset,truncation=0)
    if kind=='nb': return sm.NegativeBinomial(y,X,offset=offset)
    if kind=='logit': return sm.Logit(y,X)
    raise ValueError(kind)


def _bootstrap_fit(kind, y, X, offset, idx, start, replication):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        xx, yy = X[idx], y[idx]
        if np.linalg.matrix_rank(xx) != xx.shape[1]:
            return {'replication':replication,'status':'rank_deficient','params':None,'warnings':[]}
        try:
            mdl=_make_model(kind,yy,xx,None if offset is None else offset[idx])
            kw={'method':'newton','maxiter':200} if kind=='logit' else {'method':'bfgs','maxiter':500}
            fit=mdl.fit(start_params=start,disp=0,**kw)
            valid=bool(fit.mle_retvals.get('converged',False)) and np.isfinite(fit.params).all()
            if kind!='logit': valid = valid and fit.params[-1]>0
            return {'replication':replication,'status':'valid' if valid else 'nonconverged_or_nonfinite',
                'params':fit.params.tolist() if valid else None,
                'warnings':sorted(set(str(w.message) for w in caught))}
        except (ValueError,ArithmeticError,np.linalg.LinAlgError) as err:
            return {'replication':replication,'status':'fit_error','params':None,
                    'warnings':[str(err)]}


def state_bootstrap(kind,y,X,offset,groups,start,n,jobs,tab_dir):
    """Pairs bootstrap of states, with fixed full-estimation-frame transforms.

    Rank-deficient samples are explicitly excluded; their unidentified regional
    contrasts must not be silently assigned finite values by an optimizer.
    """
    rng=np.random.RandomState(42); groups=np.asarray(groups); states=np.unique(groups)
    draws=rng.choice(states,size=(n,len(states)),replace=True)
    index_by_state={s:np.flatnonzero(groups==s) for s in states}
    records=[]
    for begin in range(0,n,50):
        end=min(begin+50,n)
        records.extend(Parallel(n_jobs=jobs)(delayed(_bootstrap_fit)(kind,np.asarray(y,float),
            np.asarray(X,float),None if offset is None else np.asarray(offset,float),
            np.concatenate([index_by_state[s] for s in draws[i]]),np.asarray(start,float),i+1)
            for i in range(begin,end)))
        print(f'  {kind} state bootstrap: {end}/{n}',flush=True)
    valid=[v['params'] for v in records if v['status']=='valid']
    if len(valid)<max(20,.8*n):
        write_json(tab_dir/f'{kind}_bootstrap_failures.json',records)
        raise RuntimeError(f'{kind}: only {len(valid)}/{n} usable state bootstrap samples')
    vals=np.asarray(valid)
    names=list(X.columns)+(['alpha'] if kind!='logit' else [])
    qs=np.percentile(vals,[2.5,97.5],axis=0)
    meta={'requested':n,'valid':len(valid),'status_counts':dict(Counter(v['status'] for v in records)),
          'seed':42,'n_states':len(states),'ci':{name:qs[:,i].tolist() for i,name in enumerate(names)},
          'method':'state pairs; fixed transforms; full-fit starting parameters; rank-deficient draws excluded'}
    pd.DataFrame([{'replication':v['replication'],'status':v['status'],
        **dict(zip(names,v['params']))} for v in records if v['status']=='valid']).to_csv(tab_dir/f'{kind}_bootstrap_coefficients.csv',index=False)
    write_json(tab_dir/f'{kind}_bootstrap_diagnostics.json',{'summary':meta,'replications':records,'state_draws':draws.tolist()})
    return meta


def coefficient_table(fit,clustered,exog_names,bootstrap=None,scales=None):
    out={}; tcrit=stats.t.ppf(.975,26)
    ci=np.asarray(fit.conf_int()); beta=np.asarray(fit.params); se=np.asarray(clustered.bse)
    for i,name in enumerate(exog_names):
        b,s=float(beta[i]),float(se[i])
        obj={'beta':b,'se_cluster':s,'ratio':float(np.exp(b)),
            'conventional_ci':ci[i].tolist(),'cluster_ci':[b-1.96*s,b+1.96*s],
            'cluster_t_ci':[b-tcrit*s,b+tcrit*s],'p_t':float(2*stats.t.sf(abs(b/s),26))}
        if bootstrap is not None: obj['bootstrap_ci']=bootstrap['ci'][name]
        if scales is not None and name in scales:
            obj['original_unit_scale']=float(scales[name])
            if name.startswith('REGION_'): obj['whole_category_ratio']=float(np.exp(b/scales[name]))
        out[name]=obj
    return out


def flatten_coefficients(coefficients):
    rows=[]
    for name, vals in coefficients.items():
        row={'predictor':name}
        for k,v in vals.items():
            if isinstance(v,list): row[k+'_low'],row[k+'_high']=v
            else: row[k]=v
        rows.append(row)
    return pd.DataFrame(rows)


def inference(df,frame,structural,data_path,tab_dir,jobs,state_resamples):
    result={}
    for kind in ['tnb','nb']:
        print(f'  Inferential model: {kind}',flush=True)
        sub=frame[frame.NR_STATION_CNT>0] if kind=='tnb' else frame
        names=[c for c in structural if c!='POP_2024']
        scaler=StandardScaler().fit(sub[names].astype(float))
        z=pd.DataFrame(scaler.transform(sub[names].astype(float)),columns=names,index=sub.index)
        lp=np.log(sub.POP_2024); z['clogpop']=lp-lp.mean(); ex=sm.add_constant(z)
        model=_make_model(kind,sub.NR_STATION_CNT,ex,lp)
        fit=model.fit(method='bfgs',maxiter=1000,disp=0)
        clustered=model.fit(method='bfgs',maxiter=1000,disp=0,cov_type='cluster',cov_kwds={'groups':sub.MUNICIP_ID.str[:2]})
        null=_make_model(kind,sub.NR_STATION_CNT,np.ones((len(sub),1)),lp).fit(method='bfgs',maxiter=1000,disp=0)
        for label, fitted in [('main',fit),('clustered',clustered),('null',null)]:
            if not fitted.mle_retvals.get('converged',False) or not np.isfinite(fitted.params).all():
                raise RuntimeError(f'{kind} {label} model did not converge to finite parameters')
        if not np.isfinite(clustered.bse).all(): raise RuntimeError(kind+' clustered covariance is not finite')
        boot=state_bootstrap(kind,sub.NR_STATION_CNT,ex,lp,sub.MUNICIP_ID.str[:2],fit.params,
            state_resamples,jobs,tab_dir) if kind=='tnb' else None
        obj={'n':len(sub),'alpha':float(fit.params.iloc[-1]),'converged':True,'llf':float(fit.llf),
             'llnull':float(null.llf),'pseudo_r2_mcfadden':float(1-fit.llf/null.llf),
             'llr_p':float(stats.chi2.sf(2*(fit.llf-null.llf),ex.shape[1]-1)),
             'offset':'log population','centered_log_population_mean':float(lp.mean()),
             'standardization_means':dict(zip(names,scaler.mean_.tolist())),
             'standardization_scales':dict(zip(names,scaler.scale_.tolist())),
             'coefficients':coefficient_table(fit,clustered,ex.columns,boot,dict(zip(names,scaler.scale_)))}
        if boot: obj['bootstrap']=boot
        result[kind]=obj
        flatten_coefficients(obj['coefficients']).to_csv(tab_dir/('table15_truncated_nb.csv' if kind=='tnb' else 'table16_unconditional_nb.csv'),index=False)
        write_json(tab_dir/'inference_checkpoint.json',result)
    X=frame[structural].astype(float); scale=StandardScaler().fit(X)
    z=pd.DataFrame(scale.transform(X),columns=structural,index=frame.index); ex=sm.add_constant(z)
    y=frame.HIGH_SLP
    fit=sm.Logit(y,ex).fit(disp=0)
    clustered=sm.Logit(y,ex).fit(disp=0,cov_type='cluster',cov_kwds={'groups':frame.MUNICIP_ID.str[:2]})
    if not fit.mle_retvals['converged'] or not clustered.mle_retvals['converged']:
        raise RuntimeError('SLP inferential logistic did not converge')
    boot=state_bootstrap('logit',y,ex,None,frame.MUNICIP_ID.str[:2],fit.params,state_resamples,jobs,tab_dir)
    coeffs=coefficient_table(fit,clustered,ex.columns,boot,dict(zip(structural,scale.scale_)))
    for obj in coeffs.values():
        for k in ['conventional_ci','cluster_ci','cluster_t_ci','bootstrap_ci']:
            obj['or_'+k]=np.exp(obj[k]).tolist()
    result['slp']={'n':len(frame),'converged':True,'pseudo_r2_mcfadden':float(fit.prsquared),
                   'llr_p':float(fit.llr_pvalue),'coefficients':coeffs,'bootstrap':boot}
    flatten_coefficients(coeffs).to_csv(tab_dir/'table18_slp_odds_ratios.csv',index=False)
    raw=pd.read_csv(data_path,dtype={'MUNICIP_ID':str}).drop_duplicates()
    sensitivity={}; rows=[]
    classifier=Pipeline([('scale',StandardScaler()),('clf',LogisticRegression(class_weight='balanced',max_iter=2000,random_state=42))])
    for agg,pct in [('sum',.75),('max',.75),('mean',.75),('first',.75),('sum',.70),('sum',.80)]:
        counts=raw.groupby('MUNICIP_ID').SLP_STATION_CNT.agg(agg).reindex(df.MUNICIP_ID).to_numpy()
        intensity=pd.Series(1e5*counts/df.POP_2024.to_numpy(),index=df.MUNICIP_ID)
        thr=float(intensity.quantile(pct))
        target=(intensity.reindex(frame.MUNICIP_ID).reset_index(drop=True)>thr).astype(int)
        xt,xe,yt,ye=train_test_split(X,target,test_size=.25,stratify=target,random_state=42)
        prob=clone(classifier).fit(xt,yt).predict_proba(xe)[:,1]
        inf=sm.Logit(target,ex).fit(disp=0)
        if not inf.mle_retvals['converged']: raise RuntimeError('SLP sensitivity did not converge')
        spec=f'{agg}_p{int(pct*100)}'
        obj={'threshold':thr,'target_agreement':float((target==y).mean()),'auc':float(roc_auc_score(ye,prob)),
             'odds_ratios':np.exp(inf.params).to_dict()}
        sensitivity[spec]=obj; rows.append({'specification':spec,'threshold':thr,
            'target_agreement':obj['target_agreement'],'auc':obj['auc'],**{f'OR_{k}':v for k,v in obj['odds_ratios'].items()}})
    result['slp_sensitivity']=sensitivity
    pd.DataFrame(rows).to_csv(tab_dir/'table20_slp_sensitivity.csv',index=False)
    ols=sm.OLS(np.log1p(frame.SLP_PER_100K_POP),ex).fit(cov_type='cluster',cov_kwds={'groups':frame.MUNICIP_ID.str[:2]},use_t=True)
    tcrit=stats.t.ppf(.975,26)
    result['slp_ols']={'r2':float(ols.rsquared),'coefficients':{
        name:{'beta':float(ols.params[name]),'cluster_t_ci':[float(ols.params[name]-tcrit*ols.bse[name]),float(ols.params[name]+tcrit*ols.bse[name])]}
        for name in ex.columns}}
    return result


def run(df,frame,structural,baseline,data_path,tab_dir,fig_dir,jobs=4,state_resamples=999):
    tab_dir,fig_dir=Path(tab_dir),Path(fig_dir)
    p=predictive(frame,structural,baseline,tab_dir,fig_dir,jobs)
    r=ridge_intervals(frame,structural,tab_dir)
    i=inference(df,frame,structural,data_path,tab_dir,jobs,state_resamples)
    result={'predictive':p,'ridge':r,'inference':i,
        'protocol':{'split_seeds':[42,2026],'metric_bootstrap_seed':42,'metric_bootstrap_resamples':1000,
        'state_bootstrap_seed':42,'state_bootstrap_resamples':state_resamples,'rf_grid':RF_GRID,
        'rf_class_weight':'balanced','validation':'repeated fixed-configuration CV; not nested selection validation',
        'permutation_repeats':20,'region_scaling':'standardized for inference, within each estimation frame'}}
    write_json(tab_dir/'extended_results.json',result)
    return result

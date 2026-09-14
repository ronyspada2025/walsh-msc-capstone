"""Export report-numbered tables and conceptual/workflow diagrams."""
from pathlib import Path
import shutil
import pandas as pd
from .report_analysis import write_json


def diagrams(fig_dir):
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
    def render(name,title,boxes,edges):
        fig,ax=plt.subplots(figsize=(12,8)); ax.set(xlim=(0,12),ylim=(0,8)); ax.axis('off')
        for x,y,text,color in boxes:
            ax.add_patch(FancyBboxPatch((x,y),3.25,1.3,boxstyle='round,pad=0.12',facecolor=color,edgecolor='#31536b'))
            ax.text(x+1.625,y+.65,text,ha='center',va='center',fontsize=10,linespacing=1.5)
        for (x1,y1),(x2,y2) in edges:
            ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle='-|>',mutation_scale=14,color='#31536b'))
        ax.set_title(title,fontsize=16,pad=15)
        fig.tight_layout(); fig.savefig(fig_dir/name,dpi=200); plt.close(fig)
    render('figure01_conceptual_framework.png','Municipal structure and licensed NR infrastructure',[
        (.3,5.8,'Structural characteristics\nPopulation, density, income\nFiber and LTE intensity','#f8e6cb'),
        (4.3,5.8,'RQ1: High NR count\nCount and per-capita targets\nRandom forest classification','#dbeaf4'),
        (8.3,5.8,'RQ2: Presence\nAny licensed NR station\nLogistic discrimination','#dbeaf4'),
        (8.3,2.7,'RQ2: Conditional intensity\nPositive NR counts, offset\nZero-truncated NB','#e0efdc'),
        (4.3,2.7,'RQ3: Infrastructure profiles\nClustering and stability\nAssociation with region','#e0efdc'),
        (.3,2.7,'RQ4: SLP intensity\nExploratory extension\nPrivate-network-related proxy','#f4dddd')],
        [((3.68,6.45),(4.15,6.45)),((9.9,5.68),(9.9,4.12)),
         ((1.9,5.68),(1.9,4.12))])
    render('figure10_workflow.png','Executable workflow from the preserved analysis input',[
        (.3,5.8,'Preserved municipal CSV\nVerify SHA-256\nHistorical raw snapshots unavailable','#f8e6cb'),
        (4.3,5.8,'Cleaning and features\nDeduplicate and aggregate\nOne row per municipality','#dbeaf4'),
        (8.3,5.8,'Structural predictor set\nCommon modeling frame\nExclude near-target predictors','#dbeaf4'),
        (8.3,2.7,'Core and supplementary models\nRF, hurdle/NB, ridge\nK-means and SLP logistic','#e0efdc'),
        (4.3,2.7,'Validation and inference\nRepeated/state CV, splits\nPermutation and state bootstrap','#e0efdc'),
        (.3,2.7,'Export and verify\nTables, figures, predictions\nFinal report result checks','#f4dddd')],
        [((3.68,6.45),(4.15,6.45)),((7.68,6.45),(8.15,6.45)),((9.9,5.68),(9.9,4.12)),
         ((8.15,3.35),(7.68,3.35)),((4.15,3.35),(3.68,3.35))])
    shutil.copyfile(fig_dir/'figure10_workflow.png',fig_dir/'figure00_workflow.png')


def build(df,frame,r,tab_dir,fig_dir):
    tab_dir,fig_dir=Path(tab_dir),Path(fig_dir)
    diagrams(fig_dir)
    aliases={'table06_descriptives.csv':'table08_descriptives.csv','table07_missingness.csv':'table09_missingness.csv',
             'table08_speed_by_stage.csv':'table10_speed_by_stage.csv','rq3_cluster_profiles.csv':'table17_cluster_profiles.csv'}
    for old,new in aliases.items(): shutil.copyfile(tab_dir/old,tab_dir/new)
    pd.DataFrame([{'raw_rows':r['raw_shape'][0],'raw_columns':r['raw_shape'][1],
        'unique_municipalities':r['raw_unique_municipalities'],'exact_duplicates':r['exact_duplicate_rows_dropped'],
        'duplicate_key_rows':r['duplicate_key_rows'],'clean_rows':r['clean_rows'],
        'columns_before_targets':r['clean_columns'],'columns_after_targets':len(df.columns),
        'model_rows':r['model_n']}]).to_csv(tab_dir/'table04_dataset_structure.csv',index=False)
    pd.DataFrame([{'operation':'drop exact duplicates','affected_rows':r['exact_duplicate_rows_dropped']},
        {'operation':'collapse duplicate keys; SLP sum; other values first non-null','affected_rows':r['duplicate_key_rows']},
        {'operation':'drop incomplete modeling rows','affected_rows':len(df)-len(frame)}]).to_csv(tab_dir/'table05_cleaning_log.csv',index=False)
    percap=r['extended']['predictive']['percap']['42']
    rows=[]
    for label,key in [('naive P75','rq1_naive_p75'),('count P75','rq1_leakage_free_p75'),('count P70','rq1_leakage_free_p70'),('count P80','rq1_leakage_free_p80')]:
        obj=r[key]; rows.append({'specification':label,**{k:obj[k] for k in ['accuracy','f1','roc_auc','positive_share','cv_f1_mean','cv_f1_sd']}})
    pc=r['revision']['rq1_per_capita_p75']
    rows.append({'specification':'per-capita; count settings',**{k:pc[k] for k in ['accuracy','f1','roc_auc','positive_share']}})
    rows.append({'specification':'per-capita; re-tuned','accuracy':percap['accuracy'],'f1':percap['f1'],'roc_auc':percap['auc'],
        'positive_share':float((frame.NR_PER_100K_POP>frame.NR_PER_100K_POP.quantile(.75)).mean()),
        'cv_f1_mean':percap['training_cv']['f1']['mean'],'cv_f1_sd':percap['training_cv']['f1']['sd']})
    pd.DataFrame(rows).to_csv(tab_dir/'table12_rq1_performance.csv',index=False)
    rows=[]
    for model,key in [('count','rq1_cv_random_vs_state'),('slp','rq4_cv_random_vs_state')]:
        for scheme,obj in r['revision'][key].items(): rows.append({'model':model,'scheme':scheme,
            'f1_mean':obj['f1']['mean'],'f1_sd':obj['f1']['sd'],'auc_mean':obj['roc_auc']['mean'],'auc_sd':obj['roc_auc']['sd']})
    for scheme,key in [('repeated 5x5; report random-row convention','repeated_cv'),('grouped_by_state','state_cv')]:
        obj=r['extended']['predictive']['presence'][key]
        rows.append({'model':'presence','scheme':scheme,'f1_mean':obj['f1']['mean'],
                     'f1_sd':obj['f1']['sd'],'auc_mean':obj['roc_auc']['mean'],'auc_sd':obj['roc_auc']['sd']})
    pd.DataFrame(rows).to_csv(tab_dir/'table13_state_validation.csv',index=False)
    rows=[]
    for model in ['count','percap','presence','slp']:
        obj=r['extended']['predictive'][model]['42']
        rows.append({'model':model,'metric':'ROC-AUC','value':obj['auc'],
                     'ci_low':obj['auc_bootstrap']['ci'][0],'ci_high':obj['auc_bootstrap']['ci'][1]})
    for model in ['raw','log','conditional_log']:
        obj=r['extended']['ridge'][model]
        rows.append({'model':'ridge '+model,'metric':'held-out R2','value':obj['r2'],
                     'ci_low':obj['r2_bootstrap']['ci'][0],'ci_high':obj['r2_bootstrap']['ci'][1]})
    for model in ['tnb','nb']:
        obj=r['extended']['inference'][model]
        rows.append({'model':model,'metric':'McFadden pseudo-R2','value':obj['pseudo_r2_mcfadden']})
    rows.append({'model':'k-means','metric':'silhouette','value':r['rq3_silhouettes'][2]})
    pd.DataFrame(rows).to_csv(tab_dir/'table11_model_comparison.csv',index=False)
    write_json(tab_dir/'data_quality_caveats.json',{'nr_missing':int(df.NR_STATION_CNT.isna().sum()),
        'nr_observed_zero':int((df.NR_STATION_CNT==0).sum()),
        'historical_stage_no_nr_includes_unknown':r['stage_counts']['No NR station'],
        'historical_clean_column_count_is_before_targets':True,
        'source_scope':'frozen merged input; historical raw snapshots and SLP grain not authenticated'})
    write_json(tab_dir/'report_artifact_map.json',{'tables_4_5':'table04_dataset_structure.csv; table05_cleaning_log.csv',
        'tables_8_to_20':'report-numbered table CSV files in this directory',
        'tables_1_2_3_6_7':'conceptual/literature/source/dictionary/power documentation; not fitted numerical outputs',
        'figure_1':'figure01_conceptual_framework.png','figure_2':'figure00b_source_merge.png',
        'figures_3_to_9':['figure01_missingness.png','figure02_distributions.png','figure03_log1p.png','figure04_correlation.png',
                           'figure05_speed_by_stage.png','figure06_region_share.png','figure07_fiber_vs_sa.png'],
        'figure_10':'figure10_workflow.png','figure_11':'figure11_permutation_importance.png',
        'supplementary_figure_12':'figure12_roc_curves.png'})


def publish(stage,output):
    """Publish a complete generation, rolling back if a move fails."""
    import tempfile
    stage,output=Path(stage),Path(output)
    with tempfile.TemporaryDirectory(prefix='.capstone-backup-',dir=output.parent) as old:
        backup=Path(old); saved=[]; published=[]
        try:
            for file in list(stage.iterdir()):
                destination=output/file.name
                if destination.exists():
                    shutil.move(str(destination),str(backup/file.name)); saved.append(file.name)
                shutil.move(str(file),str(destination)); published.append(file.name)
        except BaseException:
            for name in published:
                p=output/name
                if p.is_dir(): shutil.rmtree(p)
                elif p.exists(): p.unlink()
            for name in saved: shutil.move(str(backup/name),str(output/name))
            raise

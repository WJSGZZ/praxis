"""Expand explicitly addressed scientific facts without evaluating document code.

CLI only; rendering, scientific execution and independent reviews remain separate.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

MAX_JSON_BYTES = 250_000_000
KEY = re.compile(r'[A-Za-z][A-Za-z0-9_.-]{0,119}\Z')
FORMAT = re.compile(r'(?:,?d|,?\.\d{1,2}[fg]|s)\Z')
MACRO = re.compile(r'\\fact\{([A-Za-z][A-Za-z0-9_.-]{0,119})\}')


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def _pairs(items):
    out = {}
    for k,v in items:
        if k in out:
            raise ValueError('Duplicate JSON key: '+k)
        out[k]=v
    return out


def _reject(value):
    raise ValueError('Nonfinite JSON: '+str(value))


def _float(value):
    x=float(value)
    return x if math.isfinite(x) else _reject(value)


def read_json(path):
    path=Path(path)
    if path.stat().st_size>MAX_JSON_BYTES:
        raise ValueError('JSON exceeds bounded file size')
    return json.loads(path.read_bytes().decode('utf-8'),object_pairs_hook=_pairs,parse_constant=_reject,parse_float=_float)


def pointer(value,path):
    """Non-root RFC6901 pointer, with canonical nonnegative array indices."""
    if not isinstance(path,str) or not path.startswith('/') or path=='/' or re.search(r'~(?![01])',path):
        raise ValueError('Invalid non-root JSON pointer')
    try:
        for token in path.split('/')[1:]:
            token=token.replace('~1','/').replace('~0','~')
            if isinstance(value,list):
                if not re.fullmatch(r'0|[1-9][0-9]*',token):
                    raise ValueError('Invalid array index')
                value=value[int(token)]
            elif isinstance(value,dict):
                value=value[token]
            else:
                raise ValueError('Pointer traverses scalar')
        return value
    except (KeyError,IndexError,OverflowError) as e:
        raise ValueError('Unresolved pointer: '+path) from e


def _inside(root,name):
    if not isinstance(name,str) or not name or Path(name).is_absolute():
        raise ValueError('Expected relative source path')
    candidate=root/name
    cursor=root
    for component in Path(name).parts:
        cursor /= component
        if cursor.is_symlink():
            raise ValueError('Source symlink refused')
    path=candidate.resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError('Source path escapes boundary or missing')
    return path


def _number(x):
    if type(x) not in (int,float) or not math.isfinite(x):
        raise ValueError('Expected finite number (not boolean)')
    return x


def _select_run(case,run_id,historical):
    if run_id is not None and (not isinstance(run_id,str) or not re.fullmatch(r'[A-Za-z0-9_-]+',run_id)):
        raise ValueError('Unsafe run id')
    if historical and run_id is None:
        raise ValueError('Historical reproduction needs explicit run id')
    if not historical:
        from scripts import pipeline
        report=pipeline.status(case)
        rows=report['runs']
        if not rows or not rows[-1]['usable_automatic_evidence']:
            raise ValueError('Latest run is not usable; do not fall back')
        latest=Path(rows[-1]['run']).name
        if run_id is not None and run_id!=latest:
            raise ValueError('Explicit old run needs historical reproduction mode')
        run_id=latest
    run=case/'runs'/run_id
    if (case/'runs').is_symlink() or run.is_symlink():
        raise ValueError('Run symlink refused')
    if not run.resolve().is_relative_to((case/'runs').resolve()):
        raise ValueError('Run escapes case')
    receipt=read_json(run/'receipt.json')
    if receipt.get('automatic_checks_passed') is not True:
        raise ValueError('Selected run did not pass automatic checks')
    return run,receipt


def resolve(case,manifest,run_id=None,*,workspace=None,historical=False):
    """Resolve one run plus explicit supplementary evidence; never run science."""
    case=Path(case).resolve();workspace=Path(workspace or Path.cwd()).resolve()
    if not case.is_relative_to(workspace):
        raise ValueError('Case must stay inside workspace')
    m=read_json(manifest) if isinstance(manifest,(str,Path)) else manifest
    if not isinstance(m,dict) or type(m.get('schema')) is not int or m['schema']!=1:
        raise ValueError('Unsupported facts schema')
    if not isinstance(m.get('facts'),dict) or not isinstance(m.get('sources'),dict):
        raise ValueError('Expected sources and facts objects')
    if historical:
        run,receipt=_select_run(case,run_id,historical)
    else:
        from scripts import pipeline
        previous_workspace=pipeline.PROJECT
        try:
            pipeline.PROJECT=workspace
            run,receipt=_select_run(case,run_id,historical)
        finally:
            pipeline.PROJECT=previous_workspace
    data={};sources={}
    for sid,spec in m['sources'].items():
        if not KEY.fullmatch(sid) or not isinstance(spec,dict):
            raise ValueError('Invalid source id/definition')
        kind=spec.get('kind')
        if kind=='run_result':
            name=spec.get('file');path=_inside(run,name)
            expected=receipt.get('outputs',{}).get(name)
            if not isinstance(expected,str):
                raise ValueError('Run source missing output binding')
        elif kind=='supplementary_evidence':
            path=_inside(workspace,spec.get('path'));expected=spec.get('sha256')
            if not isinstance(spec.get('scope'),str) or not spec['scope'].strip():
                raise ValueError('Supplement needs original scope')
        else:
            raise ValueError('Unsupported source kind')
        if path.stat().st_size>MAX_JSON_BYTES:
            raise ValueError('JSON exceeds bounded file size')
        raw=path.read_bytes()
        actual=hashlib.sha256(raw).hexdigest()
        if expected!=actual:
            raise ValueError('Source hash mismatch: '+sid)
        data[sid]=json.loads(raw.decode('utf-8'),object_pairs_hook=_pairs,parse_constant=_reject,parse_float=_float)
        sources[sid]={**spec,'path':str(path),'sha256':actual}
    def expression(node,depth=0):
        if depth>20:
            raise ValueError('Expression depth exceeded')
        if type(node) in (int,float):
            return _number(node),[]
        if not isinstance(node,dict):
            raise ValueError('Expected bounded presentation expression')
        if 'source' in node:
            sid=node['source']
            if sid not in data:
                raise ValueError('Unknown source: '+str(sid))
            p=node.get('pointer');value=pointer(data[sid],p)
            guard=node.get('guard')
            guards=node.get('guards',[])+([guard] if guard else [])
            for g in guards:
                if not isinstance(g,dict) or pointer(data[sid],g.get('pointer'))!=g.get('equals'):
                    raise ValueError('Semantic guard failed')
            return value,[{'source':sid,'pointer':p,'sha256':sources[sid]['sha256']}]
        op=node.get('op');args=node.get('args')
        if not isinstance(args,list) or len(args)>20:
            raise ValueError('Bounded expression arguments required')
        parts=[expression(x,depth+1) for x in args];values=[x[0] for x in parts];lineage=[v for x in parts for v in x[1]]
        if op in ('add','subtract','multiply','divide'):
            if len(values)!=2:
                raise ValueError('Binary operator needs two operands')
            a,b=map(_number,values)
            if op=='add':value=a+b
            elif op=='subtract':value=a-b
            elif op=='multiply':value=a*b
            elif b==0:raise ValueError('Division by zero')
            else:value=a/b
            return _number(value),lineage
        if len(values)!=1 or not isinstance(values[0],list) or len(values[0])>100000:
            raise ValueError('Reduction/select needs bounded list')
        arr=values[0]
        if op=='select':
            field=node.get('field');equals=node.get('equals')
            if not isinstance(field,str) or not field.startswith('/'):
                raise ValueError('Select field must be relative JSON pointer')
            selected=[row for row in arr if pointer(row,field)==equals]
            project=node.get('project')
            return ([pointer(row,project) for row in selected] if project else selected),lineage
        if op=='count':return len(arr),lineage
        if op=='count_where':
            predicates=node.get('predicates')
            if not isinstance(predicates,list) or not 1<=len(predicates)<=5:
                raise ValueError('Bounded predicates required')
            def matches(row,p):
                v=pointer(row,p['pointer']);cmp=p.get('comparison')
                if cmp=='positive':return _number(v)>0
                if cmp=='true':return v is True
                raise ValueError('Unsupported predicate')
            return sum(all(matches(row,p) for p in predicates) for row in arr),lineage
        if op=='min_flat':
            if any(not isinstance(a,list) for a in arr) or sum(map(len,arr))>100000:
                raise ValueError('Bounded nested numeric list required')
            arr=[x for a in arr for x in a]
            op='min'
        if op in ('min','max','sum'):
            if not arr:raise ValueError('Empty reduction')
            arr=list(map(_number,arr));return {'min':min,'max':max,'sum':sum}[op](arr),lineage
        raise ValueError('Unsupported expression operator')
    facts={}
    for key,spec in m['facts'].items():
        if not KEY.fullmatch(key) or not isinstance(spec,dict):
            raise ValueError('Invalid fact key/definition')
        unit=spec.get('unit');fmt=spec.get('format')
        if not isinstance(unit,str) or not unit.strip() or not isinstance(fmt,str) or not FORMAT.fullmatch(fmt):
            raise ValueError('Explicit unit and bounded format required')
        if re.search(r'\.(\d+)',fmt) and int(re.search(r'\.(\d+)',fmt)[1])>12:
            raise ValueError('Display precision exceeds limit')
        if 'expression' in spec and ('source' in spec or spec.get('classification')!='derived_presentation'):
            raise ValueError('Derived expression must have exclusive declared presentation role')
        value,lineage=expression(spec['expression'] if 'expression' in spec else spec)
        if not lineage:
            raise ValueError('Fact requires explicit source lineage; literals are not scientific result bindings')
        scale=_number(spec.get('scale',1))
        if fmt=='s':
            if not isinstance(value,str) or scale!=1 or not re.fullmatch(r'[A-Za-z0-9 .,+()/_-]{1,100}',value):
                raise ValueError('Unsafe text fact')
            display=value
        else:
            number=_number(_number(value)*scale)
            if fmt.endswith('d'):
                if number!=int(number):raise ValueError('Integer display cannot truncate')
                number=int(number)
            display=format(number,fmt)
        facts[key]={'raw':value,'display':display,'unit':unit,'format':fmt,'scale':scale,'classification':spec.get('classification','result'),'lineage':lineage,'expression':spec.get('expression'),'guard':spec.get('guard'),'guards':spec.get('guards',[])}
    return {'schema':1,'manifest_sha256':hashlib.sha256(json.dumps(m,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest(),'run_id':run.name,'receipt_sha256':digest(run/'receipt.json'),'mode':'historical-reproduction' if historical else 'current-usable-run','sources':sources,'facts':facts,'note':'Addressed display reproduction is not independent scientific validation'}


def _sentence(text,start,end):
    # Decimal/key periods are not sentence boundaries; preserve exact original prose.
    stops=[m.end() for m in re.finditer(r'[.!?](?=\s|$)',text)]
    a=max([0]+[i for i in stops if i<=start]);b=min([len(text)]+[i for i in stops if i>=end])
    return text[a:b].strip()


def expand(source_root,destination,manifest,*,case,run_id=None,workspace=None,historical=False):
    """Validate all sources/macros first, then create an exclusive revision tree."""
    if Path(source_root).is_symlink():raise ValueError('Source root symlink refused')
    source_root=Path(source_root).resolve();destination=Path(destination)
    boundary=Path(workspace or Path.cwd()).resolve()
    if not source_root.is_relative_to(boundary) or not destination.resolve().is_relative_to(boundary):
        raise ValueError('Expansion must stay inside workspace')
    if destination.exists() or destination.resolve().is_relative_to(source_root):
        raise ValueError('Destination must be new and outside source tree')
    result=resolve(case,manifest,run_id,workspace=workspace,historical=historical)
    prepared=[];occurrences=[]
    for path in sorted(source_root.rglob('*')):
        if path.is_symlink():raise ValueError('Source symlinks refused')
        if not path.is_file():continue
        # Copy source resources, not prior delivery/build artifacts or executables.
        if path.suffix.lower() not in {'.tex', '.json', '.png', '.jpg', '.jpeg', '.svg', '.csv'}:
            continue
        if path.name.endswith(('.build.json', '.receipt.json')) or path.name=='facts-resolution.json':
            continue
        if any(part in {'__pycache__', '.git', '.session'} for part in path.relative_to(source_root).parts):
            continue
        rel=path.relative_to(source_root);raw=path.read_bytes()
        if path.suffix=='.tex':
            text=raw.decode('utf-8')
            def replace(match):
                key=match[1]
                if key not in result['facts']:raise ValueError('Unresolved fact: '+key)
                f=result['facts'][key];line=text.count('\n',0,match.start())+1
                a=text.rfind('\n',0,match.start())+1;b=text.find('\n',match.end())
                occurrences.append({'file':rel.as_posix(),'line':line,'start':match.start(),'end':match.end(),'key':key,'display':f['display'],'unit':f['unit'],'lineage':f['lineage'],'sentence':_sentence(text,match.start(),match.end())})
                return f['display']
            expanded=MACRO.sub(replace,text)
            if re.search(r'\\fact\b',expanded):raise ValueError('Malformed or unresolved fact macro')
            raw=expanded.encode('utf-8')
        prepared.append((rel,raw))
    destination.mkdir(parents=True,exist_ok=False)
    for rel,raw in prepared:
        p=destination/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    result['occurrences']=occurrences
    result['generated_files']={rel.as_posix():digest(destination/rel) for rel,_ in prepared}
    (destination/'facts-resolution.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return result


def compare(old,new):
    """Addressed fact differences; no value-search matching."""
    changes=[]
    for k in sorted(old['facts'].keys()|new['facts'].keys()):
        a=old['facts'].get(k);b=new['facts'].get(k)
        if a!=b:changes.append({'key':k,'old':a,'new':b,'raw_changed':a is None or b is None or a['raw']!=b['raw'],'display_changed':a is None or b is None or a['display']!=b['display'],'lineage_changed':a is None or b is None or a['lineage']!=b['lineage']})
    return {'schema':1,'changes':changes,'note':'Changed facts require statement and conclusion review'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['resolve','expand'])
    for flag in ['case','manifest','workspace','source','output']:p.add_argument('--'+flag,type=Path,required=flag in ['case','manifest'])
    p.add_argument('--run-id');p.add_argument('--historical',action='store_true');a=p.parse_args()
    if a.command=='expand':
        if a.source is None or a.output is None:p.error('expand needs --source and --output')
        r=expand(a.source,a.output,a.manifest,case=a.case,run_id=a.run_id,workspace=a.workspace,historical=a.historical)
    else:r=resolve(a.case,a.manifest,a.run_id,workspace=a.workspace,historical=a.historical)
    print(json.dumps({'run_id':r['run_id'],'mode':r['mode'],'facts':len(r['facts']),'occurrences':len(r.get('occurrences',[]))}))


if __name__=='__main__':main()

"""Kafka 4.0 native performance output contracts; no performance-capacity promises."""
import math
import re
import statistics

RATES=(200,400,800)
RECORDS,SIZE=1200,1024
PRODUCER=re.compile(r'^(\d+) records sent, ([\d.]+) records/sec \(([\d.]+) MB/sec\), ([\d.]+) ms avg latency, ([\d.]+) ms max latency, (\d+) ms 50th, (\d+) ms 95th, (\d+) ms 99th, (\d+) ms 99\.9th\.$',re.MULTILINE)


def producer_summary(text,expected_records):
    matches=list(PRODUCER.finditer(text))
    if len(matches)!=1:raise RuntimeError('Expected exactly one Kafka 4.0 final producer percentile summary')
    values=list(map(float,matches[0].groups()))
    if int(values[0])!=expected_records or not all(math.isfinite(v) and v>=0 for v in values) or values[1]<=0:
        raise RuntimeError('Producer count/rate/finite values invalid')
    if not values[5]<=values[6]<=values[7]<=values[8]<=values[4] or values[3]>values[4]:raise RuntimeError('Producer latency statistics are inconsistent')
    def metric(name):
        found=re.findall(r'(?m)^producer-metrics:'+re.escape(name)+r':\{[^}\r\n]*\}\s*:\s*([\d.Ee+-]+)\s*$',text)
        if len(found)!=1 or not math.isfinite(float(found[0])) or float(found[0])<0:raise RuntimeError('Missing/invalid native producer metric '+name)
        return float(found[0])
    errors,retries=metric('record-error-total'),metric('record-retry-total')
    if errors!=0:raise RuntimeError('Native producer reported record errors despite process exit')
    return {'acknowledged_records':int(values[0]),'achieved_records_per_second':values[1],'raw_MB_per_sec':values[2],
        'raw_unit_definition':'Kafka 4.0 MB/sec divides payload bytes by 1024^2; rounded tool output retained',
        'latency_ms':dict(zip(('average','maximum','p50','p95','p99','p999'),values[3:])),
        'record_errors':errors,'record_retries':retries,'logical_delivery_error_rate':0.0}


def consumer_summary(text,expected_records,size):
    header='start.time, end.time, data.consumed.in.MB, MB.sec, data.consumed.in.nMsg, nMsg.sec, rebalance.time.ms, fetch.time.ms, fetch.MB.sec, fetch.nMsg.sec'
    if text.count(header)!=1:raise RuntimeError('Kafka 4.0 consumer summary header missing/ambiguous')
    candidates=[]
    for line in text.splitlines():
        fields=[f.strip() for f in line.split(',')]
        if len(fields)==10 and re.fullmatch(r'\d{4}-\d\d-\d\d .*',fields[0]):candidates.append(fields)
    if len(candidates)!=1:raise RuntimeError('Expected one native consumer final summary')
    fields=candidates[0];values=list(map(float,fields[2:]))
    if not fields[4].isdigit() or int(values[2])!=expected_records or not all(math.isfinite(v) and v>=0 for v in values[:6]) or values[3]<=0:
        raise RuntimeError('Native consumer count/rate/finite timing invalid')
    if abs(values[0]-expected_records*size/1024**2)>0.0001:raise RuntimeError('Native consumer byte total mismatch')
    if values[5]>0 and not all(math.isfinite(v) and v>=0 for v in values[6:]):raise RuntimeError('Native consumer fetch rate invalid for nonzero fetch interval')
    if values[5]==0 and not all(v>=0 for v in values[6:]):raise RuntimeError('Invalid zero-resolution fetch observation')
    return {'consumed_records':int(values[2]),'payload_MiB':values[0],'raw_MB_per_second':values[1],
            'records_per_second_including_group_join':values[3],'rebalance_ms':values[4],'fetch_ms':values[5],
            'raw_fetch_MB_per_second':values[6] if values[5]>0 else None,'fetch_records_per_second':values[7] if values[5]>0 else None,
            'fetch_rate_resolution':'MEASURED' if values[5]>0 else 'NOT_MEASURABLE_ZERO_MILLISECOND_INTERVAL','scope':'native fetch, not application processing'}


def trial_plan():
    # Balanced deterministic order gives every offered rate each order position once.
    return [{'trial':f'r{repeat+1}-rate{rate}','repeat':repeat+1,'target_records_per_second':rate,'records':RECORDS,'record_size':SIZE}
            for repeat in range(3) for rate in RATES[repeat:]+RATES[:repeat]]


def aggregate(trials):
    if len(trials)!=9:raise RuntimeError('All nine planned trials, including slow trials, must be retained')
    results=[]
    for rate in RATES:
        selected=[trial for trial in trials if trial['target_records_per_second']==rate]
        if len(selected)!=3 or {t['repeat'] for t in selected}!={1,2,3}:raise RuntimeError('Missing or duplicate repeated rate trial')
        values=[trial['producer']['achieved_records_per_second'] for trial in selected]
        if not all(math.isfinite(v) and v>0 for v in values):raise RuntimeError('Invalid throughput sample')
        results.append({'target_records_per_second':rate,'trials':3,'median_achieved_records_per_second':statistics.median(values),
            'sample_standard_deviation_records_per_second':statistics.stdev(values),'minimum':min(values),'maximum':max(values),
            'per_trial_p99_ms':[trial['producer']['latency_ms']['p99'] for trial in selected],
            'percentile_aggregation':'per-trial p99 retained; no averaged/global p99 inferred'})
    return results

\set ON_ERROR_STOP on
BEGIN READ ONLY;
SET LOCAL statement_timeout = '3s';
SET LOCAL lock_timeout = '500ms';
SELECT attname, null_frac, avg_width, n_distinct, correlation
FROM pg_stats WHERE schemaname='c028_stats' AND tablename='correlated'
ORDER BY attname;
SELECT attname, attstattarget
FROM pg_attribute WHERE attrelid='c028_stats.correlated'::regclass
AND attnum>0 AND NOT attisdropped ORDER BY attnum;
SELECT statistics_name, attnames, kinds, n_distinct, dependencies,
       cardinality(most_common_freqs) AS mcv_entries
FROM pg_stats_ext WHERE schemaname='c028_stats' AND tablename='correlated'
ORDER BY statistics_name;
SELECT last_analyze,last_autoanalyze,n_mod_since_analyze
FROM pg_stat_user_tables WHERE schemaname='c028_stats' AND relname='correlated';
ROLLBACK;

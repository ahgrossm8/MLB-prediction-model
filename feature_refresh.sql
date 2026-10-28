----------------------------------------------------------------------------
--HITTER LEVEL DATA
----------------------------------------------------------------------------

create or replace table `mlb_model_updated.hitter_game_log` as 
select 
  game_date,
  batter,
  sum(case when events is not null then 1 else 0 end) as  plate_appearances,
  sum(case when events is not null and events not in ('sac_fly', 'intent_walk','hit_by_pitch', 'catcher_inter', 'sac_bunt', 'walk', 'truncated_pa') then 1 else 0 end) as at_bats,
  sum(case when events in ('double', 'single', 'triple', 'home_run') then 1 else 0 end) as hits,
  sum(case when events = 'walk' then 1 else 0 end) as walks,
  sum(case when events = 'intent_walk' then 1 else 0 end) as IBB,
  sum(case when events = 'single' then 1 else 0 end) as singles,
  sum(case when events = 'double' then 1 else 0 end) as doubles,
  sum(case when events = 'triple' then 1 else 0 end) as triples,
  sum(case when events = 'home_run' then 1 else 0 end) as home_runs,
  sum(case when events in ('strikeout_double_play', 'strikeout') then 1 else 0 end) as strikeouts,
  sum(case when events = 'single' then 1 when events = 'double' then 2 when events = 'triple' then 3 when events = 'home_run' then 4 else 0 end) as total_bases,
  sum(case when events = 'hit_by_pitch' then 1 else 0 end) as hbp,
  sum(case when events = 'sac_bunt' then 1 else 0 end) as SH,
  sum(case when events = 'sac_fly' then 1 else 0 end) as SF,
  sum(case when description in ('foul', 'swinging_strike_blocked', 'foul_tip', 'hit_into_play', 'swinging_strike') then 1 else 0 end) as swings,
  sum(case when description in ('swinging_strike_blocked', 'swinging_strike') then 1 else 0 end) as misses,
  sum(case when description = 'hit_into_play' then 1 else 0 end) as in_play,
  sum(case when description = 'hit_into_play' then hit_distance_sc else 0 end) as est_distance_traveled,
  sum(case when description = 'hit_into_play' then launch_speed else 0 end) as total_launch_speed,
  sum(case when description = 'hit_into_play' then launch_angle else 0 end) as total_launch_angle --note: need to rewrite this so that I can get true distributions instead of just averages
from `mlb_model_updated.pitch_level_data_2023_to_present`
group by 1, 2
order by 1, 2;


create or replace table `mlb_model_updated.advanced_daily_metrics` as 
WITH dates AS (
  SELECT DISTINCT
    game_date,
    batter
  FROM `mlb_model_updated.pitch_level_data_2023_to_present`
),

batted_balls AS (
  SELECT
    game_date,
    batter,
    launch_angle,
    launch_speed,
    hit_distance_sc
  FROM `mlb_model_updated.pitch_level_data_2023_to_present`
  WHERE description = 'hit_into_play'
    AND launch_angle IS NOT NULL
)

SELECT
  d.game_date,
  d.batter,
  PERCENTILE_CONT(b.launch_angle, 0.5) OVER (
    PARTITION BY d.game_date, d.batter
  ) AS med_launch_angle_30d,
  PERCENTILE_CONT(b.launch_angle, 0.1) OVER (
    PARTITION BY d.game_date, d.batter
  ) AS perctile_10_launch_angle_30d,
  PERCENTILE_CONT(b.launch_angle, 0.9) OVER (
    PARTITION BY d.game_date, d.batter
  ) AS perctile_90_launch_angle_30d,
  PERCENTILE_CONT(b.launch_angle, 0.25) OVER (
    PARTITION BY d.game_date, d.batter
  ) AS perctile_25_launch_angle_30d,
  PERCENTILE_CONT(b.launch_angle, 0.75) OVER (
    PARTITION BY d.game_date, d.batter
  ) AS perctile_75_launch_angle_30d,
  PERCENTILE_CONT(b.launch_speed, 0.5) OVER (
    PARTITION BY d.game_date, d.batter
  ) AS med_launch_speed_30d,
  PERCENTILE_CONT(b.launch_speed, 0.1) OVER (
    PARTITION BY d.game_date, d.batter
  ) AS perctile_10_launch_speed_30d,
  PERCENTILE_CONT(b.launch_speed, 0.9) OVER (
    PARTITION BY d.game_date, d.batter
  ) AS perctile_90_launch_speed_30d,
  PERCENTILE_CONT(b.launch_speed, 0.25) OVER (
    PARTITION BY d.game_date, d.batter
  ) AS perctile_25_launch_speed_30d,
  PERCENTILE_CONT(b.launch_speed, 0.75) OVER (
    PARTITION BY d.game_date, d.batter
  ) AS perctile_75_launch_speed_30d,
  PERCENTILE_CONT(b.hit_distance_sc, 0.5) OVER (
    PARTITION BY d.game_date, d.batter
  ) AS med_est_distance_30d,
  PERCENTILE_CONT(b.hit_distance_sc, 0.1) OVER (
    PARTITION BY d.game_date, d.batter
  ) AS perctile_10_est_distance_30d,
  PERCENTILE_CONT(b.hit_distance_sc, 0.9) OVER (
    PARTITION BY d.game_date, d.batter
  ) AS perctile_90_est_distance_30d,
  PERCENTILE_CONT(b.hit_distance_sc, 0.25) OVER (
    PARTITION BY d.game_date, d.batter
  ) AS perctile_25_est_distance_30d,
  PERCENTILE_CONT(b.hit_distance_sc, 0.75) OVER (
    PARTITION BY d.game_date, d.batter
  ) AS perctile_75_est_distance_30d
FROM dates d
LEFT JOIN batted_balls b
  ON b.game_date >= DATE_SUB(d.game_date, INTERVAL 30 DAY)
  AND b.game_date < d.game_date
  and b.batter = d.batter
QUALIFY ROW_NUMBER() OVER (PARTITION BY d.game_date, d.batter) = 1
ORDER BY d.game_date;


create or replace table `mlb_model_updated.game_log_advanced_stage` as
select 
  game_date,
  batter,
  at_bats,
  hits,
  singles,
  doubles,
  triples,
  home_runs,
  total_bases,
  walks,
  strikeouts,
  hbp,
  ibb,
  plate_appearances,
  sum(at_bats) OVER (
    partition by batter
    order by UNIX_DATE(game_date)
    RANGE BETWEEN 30 PRECEDING AND 1 PRECEDING
  ) as ab_30d,
  sum(hits) OVER (
    partition by batter
    order by UNIX_DATE(game_date)
    RANGE BETWEEN 30 PRECEDING AND 1 PRECEDING
  ) as hits_30d,
  SAFE_DIVIDE(
    (sum(hits) OVER (
      partition by batter
      order by UNIX_DATE(game_date)
      RANGE BETWEEN 30 PRECEDING AND 1 PRECEDING)
    )
    ,
    (sum(at_bats) OVER (
      partition by batter
      order by UNIX_DATE(game_date)
      RANGE BETWEEN 30 PRECEDING AND 1 PRECEDING))
    ) as avg_last_30_days,
    sum(plate_appearances) over(
      partition by batter
      order by unix_date(game_date) 
      range between 30 preceding and 1 preceding
      ) as pa_30d,
    safe_divide(
      (
          sum(hits) over(
          partition by batter
          order by unix_date(game_date)
          range between 30 preceding and 1 preceding
        )
        +
        sum(walks) over(
          partition by batter
          order by unix_date(game_date)
          range between 30 preceding and 1 preceding
        )
        +
        sum(IBB) over (
          partition by batter
          order by unix_date(game_date)
          range between 30 preceding and 1 preceding
        )
        +
        sum(hbp) over(
          partition by batter
          order by unix_date(game_date)
          range between 30 preceding and 1 preceding
        )
      )
      ,
      sum(plate_appearances) over(
        partition by batter
        order by unix_date(game_date)
        range between 30 preceding and 1 preceding
      ) 
    ) as obp_30d,
    safe_divide(
      sum(total_bases) over(
        partition by batter
        order by unix_date(game_date)
        range between 30 preceding and 1 preceding
      )
      ,
      sum(at_bats) over(
        partition by batter
        order by unix_date(game_date)
        range between 30 preceding and 1 preceding
      )
    ) as slugging_pct_30d,
    safe_divide(
      sum(strikeouts) over(
        partition by batter
        order by unix_date(game_date)
        range between 30 preceding and 1 preceding
      )
      ,
      sum(plate_appearances) over(
        partition by batter
        order by unix_date(game_date)
        range between 30 preceding and 1 preceding
      )
    ) as k_rate_30d,
    swings,
    misses,
    in_play,
    safe_divide(
      sum(misses) over(
        partition by batter
        order by unix_date(game_date)
        range between 30 preceding and 1 preceding 
      )
      ,
      sum(swings) over(
        partition by batter
        order by unix_date(game_date)
        range between 30 preceding and 1 preceding
      )
    ) as whiff_rate_30d,
    safe_divide(
      sum(total_launch_speed) over(
        partition by batter
        order by unix_date(game_date)
        range between 30 preceding and 1 preceding
      ),
      sum(in_play) over (
        partition by batter
        order by unix_date(game_date)
        range between 30 preceding and 1 preceding
      )
    ) as avg_30d_launch_speed,
    safe_divide(
      sum(total_launch_angle) over(
        partition by batter
        order by unix_date(game_date)
        range between 30 preceding and 1 preceding
      )
      ,
      sum(in_play) over(
        partition by batter
        order by unix_date(game_date)
        range between 30 preceding and 1 preceding
      )
    ) as avg_30d_launch_angle,
    safe_divide(
      sum(est_distance_traveled) over(
        partition by batter
        order by unix_date(game_date)
        range between 30 preceding and 1 preceding
      )
      ,
      sum(in_play) over(
        partition by batter
        order by unix_date(game_date)
        range between 30 preceding and 1 preceding
      )
    ) as avg_30d_est_distance
from `mlb_model_updated.hitter_game_log`;

create or replace table `mlb_model_updated.game_log_final` as
select
  a.game_date,
  a.batter,
  a.avg_last_30_days,
  a.obp_30d,
  a.slugging_pct_30d,
  a.obp_30d + a.slugging_pct_30d as ops_30d,
  a.k_rate_30d,
  a.whiff_rate_30d,
  a.avg_30d_est_distance,
  a.avg_30d_launch_angle,
  a.avg_30d_launch_speed,
  dm.perctile_10_launch_angle_30d,
  dm.perctile_25_launch_angle_30d,
  dm.med_launch_angle_30d,
  dm.perctile_75_launch_angle_30d,
  dm.perctile_90_launch_angle_30d,
  dm.perctile_10_launch_speed_30d,
  dm.perctile_25_launch_speed_30d,
  dm.med_launch_speed_30d,
  dm.perctile_75_launch_speed_30d,
  dm.perctile_90_launch_speed_30d,
  dm.perctile_10_est_distance_30d,
  dm.perctile_25_est_distance_30d,
  dm.med_est_distance_30d,
  dm.perctile_75_est_distance_30d,
  dm.perctile_90_est_distance_30d
from `mlb_model_updated.advanced_daily_metrics` dm
inner join `mlb_model_updated.game_log_advanced_stage` a
  on dm.game_date = a.game_date
  and dm.batter = a.batter
  ;

----------------------------------------------------------------------------
--PITCHER LEVEL DATA
----------------------------------------------------------------------------
create or replace table `mlb_model_updated.pitcher_game_log` as 
select 
  game_date,
  pitcher,
  max(
    case
      when events in ('triple', 'single', 'field_error', 'hit_by_pitch', 'intent_walk', 'walk', 'home_run', 'catcher_interf', 'double') then (inning - 1) * 3 + outs_when_up
      when events in ('grounded_into_double_play', 'strikeout_double_play', 'sac_fly_double_play', 'double_play') then (inning - 1) * 3 + outs_when_up + 2
      when events in ('strikeout', 'truncated_pa', 'sac_fly', 'fielders_choice_out', 'fielders_choice', 'field_out', 'force_out', 'sac_bunt') then (inning - 1) * 3 + outs_when_up + 1
      when events = 'triple_play' then (inning - 1) * 3 + outs_when_up + 3
      end
    ) AS outs_recorded,
  max(
    case
      when events in ('triple', 'single', 'field_error', 'hit_by_pitch', 'intent_walk', 'walk', 'home_run', 'catcher_interf', 'double') then (inning - 1) * 3 + outs_when_up
      when events in ('grounded_into_double_play', 'strikeout_double_play', 'sac_fly_double_play', 'double_play') then (inning - 1) * 3 + outs_when_up + 2
      when events in ('strikeout', 'truncated_pa', 'sac_fly', 'fielders_choice_out', 'fielders_choice', 'field_out', 'force_out', 'sac_bunt') then (inning - 1) * 3 + outs_when_up + 1
      when events = 'triple_play' then (inning - 1) * 3 + outs_when_up + 3
      end
    ) / 3 AS innings,  
  max(case when inning_topbot = 'Bot' then home_score  else away_score end) as runs_allowed,
  sum(case when description in ('ball', 'blocked_ball', 'hit_by_pitch', 'hit_into_play', 'foul', 'swinging_strike_blocked', 'bunt_foul_tip', 'foul_bunt', 'missed_bunt', 'called_strike', 'foul_tip', 'swinging_strike') then 1 else 0 end) as pitches,  
  sum(release_speed) as release_speed,
  sum(case when description in ('ball', 'blocked_ball', 'hit_by_pitch') then 1 else 0 end) as balls,
  sum(case when description in ('hit_into_play', 'foul', 'swinging_strike_blocked', 'bunt_foul_tip', 'foul_bunt', 'missed_bunt', 'called_strike', 'foul_tip', 'swinging_strike') then 1 else 0 end) as strikes,
  sum(case when events is not null then 1 else 0 end) as  plate_appearances,
  sum(case when events is not null and events not in ('sac_fly', 'intent_walk','hit_by_pitch', 'catcher_inter', 'sac_bunt', 'walk', 'truncated_pa') then 1 else 0 end) as at_bats,
  sum(case when events in ('double', 'single', 'triple', 'home_run') then 1 else 0 end) as hits,
  sum(case when events = 'walk' then 1 else 0 end) as walks,
  sum(case when events = 'intent_walk' then 1 else 0 end) as IBB,
  sum(case when events = 'single' then 1 else 0 end) as singles,
  sum(case when events = 'double' then 1 else 0 end) as doubles,
  sum(case when events = 'triple' then 1 else 0 end) as triples,
  sum(case when events = 'home_run' then 1 else 0 end) as home_runs,
  sum(case when events in ('strikeout_double_play', 'strikeout') then 1 else 0 end) as strikeouts,
  sum(case when events = 'single' then 1 when events = 'double' then 2 when events = 'triple' then 3 when events = 'home_run' then 4 else 0 end) as total_bases,
  sum(case when events = 'hit_by_pitch' then 1 else 0 end) as hbp,
  sum(case when events = 'sac_bunt' then 1 else 0 end) as SH,
  sum(case when events = 'sac_fly' then 1 else 0 end) as SF,
  sum(case when description in ('foul', 'swinging_strike_blocked', 'foul_tip', 'hit_into_play', 'swinging_strike', 'foul_bunt') then 1 else 0 end) as swings,
  sum(case when description in ('swinging_strike_blocked', 'swinging_strike') then 1 else 0 end) as misses,
  sum(case when description = 'hit_into_play' then 1 else 0 end) as in_play,
  sum(case when description = 'hit_into_play' then hit_distance_sc else 0 end) as est_distance_traveled,
  sum(case when description = 'hit_into_play' then launch_speed else 0 end) as total_launch_speed,
  sum(case when description = 'hit_into_play' then launch_angle else 0 end) as total_launch_angle --note: need to rewrite this so that I can get true distributions instead of just averages
from `mlb_model_updated.pitch_level_data_2023_to_present`
group by 1, 2
order by 2, 1
;

create or replace table `mlb_model_updated.advanced_daily_pitcher_metrics` as 
WITH dates AS (
  SELECT DISTINCT
    game_date,
    pitcher
  FROM `mlb_model_updated.pitch_level_data_2023_to_present`
),

batted_balls AS (
  SELECT
    game_date,
    pitcher,
    launch_angle,
    launch_speed,
    hit_distance_sc
  FROM `mlb_model_updated.pitch_level_data_2023_to_present`
  WHERE 
    description = 'hit_into_play'
    AND launch_angle IS NOT NULL
)

SELECT
  d.game_date,
  d.pitcher,
  PERCENTILE_CONT(b.launch_angle, 0.5) OVER (
    PARTITION BY d.game_date, d.pitcher
  ) AS med_launch_angle_30d,
  PERCENTILE_CONT(b.launch_angle, 0.1) OVER (
    PARTITION BY d.game_date, d.pitcher
  ) AS perctile_10_launch_angle_30d,
  PERCENTILE_CONT(b.launch_angle, 0.9) OVER (
    PARTITION BY d.game_date, d.pitcher
  ) AS perctile_90_launch_angle_30d,
  PERCENTILE_CONT(b.launch_angle, 0.25) OVER (
    PARTITION BY d.game_date, d.pitcher
  ) AS perctile_25_launch_angle_30d,
  PERCENTILE_CONT(b.launch_angle, 0.75) OVER (
    PARTITION BY d.game_date, d.pitcher
  ) AS perctile_75_launch_angle_30d,
  PERCENTILE_CONT(b.launch_speed, 0.5) OVER (
    PARTITION BY d.game_date, d.pitcher
  ) AS med_launch_speed_30d,
  PERCENTILE_CONT(b.launch_speed, 0.1) OVER (
    PARTITION BY d.game_date, d.pitcher
  ) AS perctile_10_launch_speed_30d,
  PERCENTILE_CONT(b.launch_speed, 0.9) OVER (
    PARTITION BY d.game_date, d.pitcher
  ) AS perctile_90_launch_speed_30d,
  PERCENTILE_CONT(b.launch_speed, 0.25) OVER (
    PARTITION BY d.game_date, d.pitcher
  ) AS perctile_25_launch_speed_30d,
  PERCENTILE_CONT(b.launch_speed, 0.75) OVER (
    PARTITION BY d.game_date, d.pitcher
  ) AS perctile_75_launch_speed_30d,
  PERCENTILE_CONT(b.hit_distance_sc, 0.5) OVER (
    PARTITION BY d.game_date, d.pitcher
  ) AS med_est_distance_30d,
  PERCENTILE_CONT(b.hit_distance_sc, 0.1) OVER (
    PARTITION BY d.game_date, d.pitcher
  ) AS perctile_10_est_distance_30d,
  PERCENTILE_CONT(b.hit_distance_sc, 0.9) OVER (
    PARTITION BY d.game_date, d.pitcher
  ) AS perctile_90_est_distance_30d,
  PERCENTILE_CONT(b.hit_distance_sc, 0.25) OVER (
    PARTITION BY d.game_date, d.pitcher
  ) AS perctile_25_est_distance_30d,
  PERCENTILE_CONT(b.hit_distance_sc, 0.75) OVER (
    PARTITION BY d.game_date, d.pitcher
  ) AS perctile_75_est_distance_30d
FROM dates d
LEFT JOIN batted_balls b
  ON b.game_date >= DATE_SUB(d.game_date, INTERVAL 30 DAY)
  AND b.game_date < d.game_date
  and b.pitcher = d.pitcher
QUALIFY ROW_NUMBER() OVER (PARTITION BY d.game_date, d.pitcher) = 1
ORDER BY d.game_date;



create or replace table `mlb_model_updated.pitch_detailed` as 
WITH pitcher_dates AS (
  SELECT DISTINCT
    pitcher,
    game_date
  FROM `mlb_model_updated.pitch_level_data_2023_to_present`
)

SELECT
  d.game_date,
  d.pitcher,
  APPROX_QUANTILES(s.release_speed, 100)[OFFSET(10)] AS release_speed_10th_percentile_30d,
  APPROX_QUANTILES(s.release_speed, 100)[OFFSET(25)] AS release_speed_25th_percentile_30d,
  APPROX_QUANTILES(s.release_speed, 100)[OFFSET(50)] AS release_speed_median_30d,
  APPROX_QUANTILES(s.release_speed, 100)[OFFSET(75)] AS release_speed_75th_percentile_30d,
  APPROX_QUANTILES(s.release_speed, 100)[OFFSET(90)] AS release_speed_90th_percentile_30d,
  STDDEV(s.release_speed) AS velo_stdev_30d,
  APPROX_QUANTILES(s.pfx_x, 100)[OFFSET(10)] AS hor_movement_10th_percentile_30d,
  APPROX_QUANTILES(s.pfx_x, 100)[OFFSET(25)] AS hor_movement_25th_percentile_30d,
  APPROX_QUANTILES(s.pfx_x, 100)[OFFSET(50)] AS hor_movement_median_30d,
  APPROX_QUANTILES(s.pfx_x, 100)[OFFSET(75)] AS hor_movement_75th_percentile_30d,
  APPROX_QUANTILES(s.pfx_x, 100)[OFFSET(90)] AS hor_movement_90th_percentile_30d,
  STDDEV(s.pfx_x) AS hor_movement_stdev_30d,
  APPROX_QUANTILES(s.pfx_z, 100)[OFFSET(10)] AS vert_movement_10th_percentile_30d,
  APPROX_QUANTILES(s.pfx_z, 100)[OFFSET(25)] AS vert_movement_25th_percentile_30d,
  APPROX_QUANTILES(s.pfx_z, 100)[OFFSET(50)] AS vert_movement_median_30d,
  APPROX_QUANTILES(s.pfx_z, 100)[OFFSET(75)] AS vert_movement_75th_percentile_30d,
  APPROX_QUANTILES(s.pfx_z, 100)[OFFSET(90)] AS vert_movement_90th_percentile_30d,
  STDDEV(s.pfx_z) AS vert_movement_stdev_30d
FROM pitcher_dates d
LEFT JOIN `mlb_model_updated.pitch_level_data_2023_to_present` s
  ON d.pitcher = s.pitcher
  AND s.game_date < d.game_date
  AND s.game_date >= DATE_SUB(d.game_date, INTERVAL 30 DAY)
  AND s.release_speed IS NOT NULL
GROUP BY
  d.pitcher,
  d.game_date
ORDER BY
  d.game_date;


create or replace table `mlb_model_updated.game_log_pitcher_advanced_stage` as 
select
  game_date,
  pitcher,
  innings,
  runs_allowed,
  at_bats,
  hits,
  singles,
  doubles,
  triples,
  home_runs,
  total_bases,
  walks,
  strikeouts,
  hbp,
  ibb,
  plate_appearances,
  safe_divide(
    sum(walks + hits) OVER(
      partition by pitcher
      order by unix_date(game_date)
      range between 30 preceding and 1 preceding
    )
    ,
    sum(innings + IBB + hbp) OVER(
      partition by pitcher
      order by unix_date(game_date)
      range between 30 preceding and 1 preceding
    )
  ) as WHIP_30d,
  9.0 * safe_divide(
    sum(runs_allowed) OVER(
      partition by pitcher
      order by unix_date(game_date)
      range between 30 preceding and 1 preceding
    )
    ,
    sum(innings) OVER(
      partition by pitcher
      order by unix_date(game_date)
      range between 30 preceding and 1 preceding
    )
  ) as ERA_30d,  
  avg(innings) over(
    partition by pitcher
    order by unix_date(game_date)
    range between 30 preceding and 1 preceding 
  ) as avg_innings_30d,
  sum(at_bats) OVER (
    partition by pitcher
    order by UNIX_DATE(game_date)
    RANGE BETWEEN 30 PRECEDING AND 1 PRECEDING
  ) as ab_30d,
  sum(hits) OVER (
    partition by pitcher
    order by UNIX_DATE(game_date)
    RANGE BETWEEN 30 PRECEDING AND 1 PRECEDING
  ) as hits_30d,
  SAFE_DIVIDE(
    (sum(hits) OVER (
      partition by pitcher
      order by UNIX_DATE(game_date)
      RANGE BETWEEN 30 PRECEDING AND 1 PRECEDING)
    )
    ,
    (sum(at_bats) OVER (
      partition by pitcher
      order by UNIX_DATE(game_date)
      RANGE BETWEEN 30 PRECEDING AND 1 PRECEDING))
    ) as avg_last_30_days,
    sum(plate_appearances) over(
      partition by pitcher
      order by unix_date(game_date) 
      range between 30 preceding and 1 preceding
      ) as pa_30d,
    safe_divide(
      (
          sum(hits) over(
          partition by pitcher
          order by unix_date(game_date)
          range between 30 preceding and 1 preceding
        )
        +
        sum(walks) over(
          partition by pitcher
          order by unix_date(game_date)
          range between 30 preceding and 1 preceding
        )
        +
        sum(IBB) over (
          partition by pitcher
          order by unix_date(game_date)
          range between 30 preceding and 1 preceding
        )
        +
        sum(hbp) over(
          partition by pitcher
          order by unix_date(game_date)
          range between 30 preceding and 1 preceding
        )
      )
      ,
      sum(plate_appearances) over(
        partition by pitcher
        order by unix_date(game_date)
        range between 30 preceding and 1 preceding
      ) 
    ) as obp_30d,
    safe_divide(
      sum(total_bases) over(
        partition by pitcher
        order by unix_date(game_date)
        range between 30 preceding and 1 preceding
      )
      ,
      sum(at_bats) over(
        partition by pitcher
        order by unix_date(game_date)
        range between 30 preceding and 1 preceding
      )
    ) as slugging_pct_30d,
    safe_divide(
      sum(strikeouts) over(
        partition by pitcher
        order by unix_date(game_date)
        range between 30 preceding and 1 preceding
      )
      ,
      sum(plate_appearances) over(
        partition by pitcher
        order by unix_date(game_date)
        range between 30 preceding and 1 preceding
      )
    ) as k_rate_30d,
    swings,
    misses,
    in_play,
    safe_divide(
      sum(misses) over(
        partition by pitcher
        order by unix_date(game_date)
        range between 30 preceding and 1 preceding 
      )
      ,
      sum(swings) over(
        partition by pitcher
        order by unix_date(game_date)
        range between 30 preceding and 1 preceding
      )
    ) as whiff_rate_30d,
    safe_divide(
      sum(total_launch_speed) over(
        partition by pitcher
        order by unix_date(game_date)
        range between 30 preceding and 1 preceding
      ),
      sum(in_play) over (
        partition by pitcher
        order by unix_date(game_date)
        range between 30 preceding and 1 preceding
      )
    ) as avg_30d_launch_speed,
    safe_divide(
      sum(total_launch_angle) over(
        partition by pitcher
        order by unix_date(game_date)
        range between 30 preceding and 1 preceding
      )
      ,
      sum(in_play) over(
        partition by pitcher
        order by unix_date(game_date)
        range between 30 preceding and 1 preceding
      )
    ) as avg_30d_launch_angle,
    safe_divide(
      sum(est_distance_traveled) over(
        partition by pitcher
        order by unix_date(game_date)
        range between 30 preceding and 1 preceding
      )
      ,
      sum(in_play) over(
        partition by pitcher
        order by unix_date(game_date)
        range between 30 preceding and 1 preceding
      )
    ) as avg_30d_est_distance,
    safe_divide(
      sum(release_speed) over(
        partition by pitcher
        order by unix_date(game_date)
        range between 30 preceding and 1 preceding
      )
      ,
      sum(pitches) over(
        partition by pitcher
        order by unix_date(game_date)
        range between 30 preceding and 1 preceding
      )
    ) as avg_velo_30d
from `mlb_model_updated.pitcher_game_log`;



create or replace table `mlb_model_updated.pitcher_game_log_final` as
select 
  a.game_date,
  a.pitcher,
  a.pa_30d,
  a.ERA_30d,
  a.WHIP_30d,
  a.avg_innings_30d,
  a.ab_30d,
  a.avg_last_30_days,
  a.obp_30d,
  a.slugging_pct_30d,
  a.k_rate_30d,
  a.whiff_rate_30d,
  a.avg_30d_launch_angle,
  a.avg_30d_launch_speed,
  a.avg_30d_est_distance,
  a.obp_30d + a.slugging_pct_30d as ops_30d,
  a.avg_velo_30d,
  adm.*  except(game_date, pitcher),
  pd.* except(game_date, pitcher)
from `mlb_model_updated.game_log_pitcher_advanced_stage` a
inner join `mlb_model_updated.advanced_daily_pitcher_metrics` adm
  on a.game_date = adm.game_date
  and a.pitcher = adm.pitcher
inner join `mlb_model_updated.pitch_detailed` pd
  on a.game_date = pd.game_date
  and a.pitcher = pd.pitcher
order by 1
;

--lineup check by game. Adjusted KPIs is a starting point from chatgpt. To account for hitters earlier in the lineup getting more ABs
create or replace table `mlb_model_updated.inputs_for_regression_stage` as 
with lineup_orders as (
select
  game_date,
  game_pk,
  case when inning_topbot = 'Top' then 'Away' else 'Home' end as team,
  batter,
  at_bat_number,
  dense_rank() over(
    partition by game_pk, inning_topbot
    order by at_bat_number
  ) as lineup_order
from `mlb_model_updated.pitch_level_data_2023_to_present`
),
lineup_detailed_stats as (
select
  lo.* except(at_bat_number, lineup_order),
  gl.avg_last_30_days,
  case
    when lo.lineup_order = 1 then avg_last_30_days * 1.15
    when lo.lineup_order = 2 then avg_last_30_days * 1.1
    when lo.lineup_order = 3 then avg_last_30_days * 1.08
    when lo.lineup_order = 4 then avg_last_30_days * 1.05
    when lo.lineup_order = 5 then avg_last_30_days * 1.0
    when lo.lineup_order = 6 then avg_last_30_days * 0.97
    when lo.lineup_order = 7 then avg_last_30_days * 0.93
    when lo.lineup_order = 8 then avg_last_30_days * 0.88
    when lo.lineup_order = 9 then avg_last_30_days * 0.84
    else null
    end as adjusted_avg_30d,
  case
    when lo.lineup_order = 1 then obp_30d * 1.15
    when lo.lineup_order = 2 then obp_30d * 1.1
    when lo.lineup_order = 3 then obp_30d * 1.08
    when lo.lineup_order = 4 then obp_30d * 1.05
    when lo.lineup_order = 5 then obp_30d * 1.0
    when lo.lineup_order = 6 then obp_30d * 0.97
    when lo.lineup_order = 7 then obp_30d * 0.93
    when lo.lineup_order = 8 then obp_30d * 0.88
    when lo.lineup_order = 9 then obp_30d * 0.84
    else null
    end as adjusted_obp_30d,
case
    when lo.lineup_order = 1 then slugging_pct_30d * 1.15
    when lo.lineup_order = 2 then slugging_pct_30d * 1.1
    when lo.lineup_order = 3 then slugging_pct_30d * 1.08
    when lo.lineup_order = 4 then slugging_pct_30d * 1.05
    when lo.lineup_order = 5 then slugging_pct_30d * 1.0
    when lo.lineup_order = 6 then slugging_pct_30d * 0.97
    when lo.lineup_order = 7 then slugging_pct_30d * 0.93
    when lo.lineup_order = 8 then slugging_pct_30d * 0.88
    when lo.lineup_order = 9 then slugging_pct_30d * 0.84
    else null
    end as adjusted_slug_30d,  
case
    when lo.lineup_order = 1 then ops_30d * 1.15
    when lo.lineup_order = 3 then ops_30d * 1.08
    when lo.lineup_order = 2 then ops_30d * 1.1
    when lo.lineup_order = 4 then ops_30d * 1.05
    when lo.lineup_order = 5 then ops_30d * 1.0
    when lo.lineup_order = 6 then ops_30d * 0.97
    when lo.lineup_order = 7 then ops_30d * 0.93
    when lo.lineup_order = 8 then ops_30d * 0.88
    when lo.lineup_order = 9 then ops_30d * 0.84
    else null
    end as adjusted_ops_30d,  
case
    when lo.lineup_order = 1 then k_rate_30d * 1.15
    when lo.lineup_order = 3 then k_rate_30d * 1.08
    when lo.lineup_order = 2 then k_rate_30d * 1.1
    when lo.lineup_order = 4 then k_rate_30d * 1.05
    when lo.lineup_order = 5 then k_rate_30d * 1.0
    when lo.lineup_order = 6 then k_rate_30d * 0.97
    when lo.lineup_order = 7 then k_rate_30d * 0.93
    when lo.lineup_order = 8 then k_rate_30d * 0.88
    when lo.lineup_order = 9 then k_rate_30d * 0.84
    else null
    end as adjusted_k_rate_30d,  
case
    when lo.lineup_order = 1 then whiff_rate_30d * 1.15
    when lo.lineup_order = 3 then whiff_rate_30d * 1.08
    when lo.lineup_order = 2 then whiff_rate_30d * 1.1
    when lo.lineup_order = 4 then whiff_rate_30d * 1.05
    when lo.lineup_order = 5 then whiff_rate_30d * 1.0
    when lo.lineup_order = 6 then whiff_rate_30d * 0.97
    when lo.lineup_order = 7 then whiff_rate_30d * 0.93
    when lo.lineup_order = 8 then whiff_rate_30d * 0.88
    when lo.lineup_order = 9 then whiff_rate_30d * 0.84
    else null
    end as adjusted_whiff_rate_30d,  
case
    when lo.lineup_order = 1 then med_launch_speed_30d * 1.15
    when lo.lineup_order = 3 then med_launch_speed_30d * 1.08
    when lo.lineup_order = 2 then med_launch_speed_30d * 1.1
    when lo.lineup_order = 4 then med_launch_speed_30d * 1.05
    when lo.lineup_order = 5 then med_launch_speed_30d * 1.0
    when lo.lineup_order = 6 then med_launch_speed_30d * 0.97
    when lo.lineup_order = 7 then med_launch_speed_30d * 0.93
    when lo.lineup_order = 8 then med_launch_speed_30d * 0.88
    when lo.lineup_order = 9 then med_launch_speed_30d * 0.84
    else null
    end as adjusted_med_launch_speed_30d,  
case
    when lo.lineup_order = 1 then perctile_90_launch_speed_30d * 1.15
    when lo.lineup_order = 3 then perctile_90_launch_speed_30d * 1.08
    when lo.lineup_order = 2 then perctile_90_launch_speed_30d * 1.1
    when lo.lineup_order = 4 then perctile_90_launch_speed_30d * 1.05
    when lo.lineup_order = 5 then perctile_90_launch_speed_30d * 1.0
    when lo.lineup_order = 6 then perctile_90_launch_speed_30d * 0.97
    when lo.lineup_order = 7 then perctile_90_launch_speed_30d * 0.93
    when lo.lineup_order = 8 then perctile_90_launch_speed_30d * 0.88
    when lo.lineup_order = 9 then perctile_90_launch_speed_30d * 0.84
    else null
    end as adjusted_pctl_90_launch_speed_30d,  
case
    when lo.lineup_order = 1 then med_launch_angle_30d * 1.15
    when lo.lineup_order = 3 then med_launch_angle_30d * 1.08
    when lo.lineup_order = 2 then med_launch_angle_30d * 1.1
    when lo.lineup_order = 4 then med_launch_angle_30d * 1.05
    when lo.lineup_order = 5 then med_launch_angle_30d * 1.0
    when lo.lineup_order = 6 then med_launch_angle_30d * 0.97
    when lo.lineup_order = 7 then med_launch_angle_30d * 0.93
    when lo.lineup_order = 8 then med_launch_angle_30d * 0.88
    when lo.lineup_order = 9 then med_launch_angle_30d * 0.84
    else null
    end as adjusted_med_launch_angle_30d,  
case
    when lo.lineup_order = 1 then med_est_distance_30d * 1.15
    when lo.lineup_order = 3 then med_est_distance_30d * 1.08
    when lo.lineup_order = 2 then med_est_distance_30d * 1.1
    when lo.lineup_order = 4 then med_est_distance_30d * 1.05
    when lo.lineup_order = 5 then med_est_distance_30d * 1.0
    when lo.lineup_order = 6 then med_est_distance_30d * 0.97
    when lo.lineup_order = 7 then med_est_distance_30d * 0.93
    when lo.lineup_order = 8 then med_est_distance_30d * 0.88
    when lo.lineup_order = 9 then med_est_distance_30d * 0.84
    else null
    end as adjusted_med_est_distance_30d,  
case
    when lo.lineup_order = 1 then perctile_90_est_distance_30d * 1.15
    when lo.lineup_order = 3 then perctile_90_est_distance_30d * 1.08
    when lo.lineup_order = 2 then perctile_90_est_distance_30d * 1.1
    when lo.lineup_order = 4 then perctile_90_est_distance_30d * 1.05
    when lo.lineup_order = 5 then perctile_90_est_distance_30d * 1.0
    when lo.lineup_order = 6 then perctile_90_est_distance_30d * 0.97
    when lo.lineup_order = 7 then perctile_90_est_distance_30d * 0.93
    when lo.lineup_order = 8 then perctile_90_est_distance_30d * 0.88
    when lo.lineup_order = 9 then perctile_90_est_distance_30d * 0.84
    else null
    end as adjusted_pctl_90_est_distance_30d,  
    min(lo.lineup_order) as lineup_order
from lineup_orders lo
join `mlb_model_updated.game_log_final` gl
  on lo.game_date = gl.game_date
  and lo.batter = gl.batter
where lo.lineup_order <= 9
group by 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16
order by lo.game_pk, lo.game_date, lo.team, lineup_order
),
lineups_final_stag as (
select
  game_date,
  game_pk,
  team,
  avg(adjusted_avg_30d) as proj_team_avg,
  avg(adjusted_obp_30d) as proj_team_obp,
  avg(adjusted_slug_30d) as proj_team_slug,
  avg(adjusted_ops_30d) as proj_team_ops,
  avg(adjusted_k_rate_30d) as proj_team_k_rate,
  avg(adjusted_whiff_rate_30d) as proj_team_whiff_rate,
  avg(adjusted_med_launch_speed_30d) as proj_team_med_launch_speed,
  avg(adjusted_pctl_90_launch_speed_30d) as proj_team_high_launch_speed,
  avg(adjusted_med_launch_angle_30d) as proj_team_med_launch_angle,
  avg(adjusted_med_est_distance_30d) as proj_team_med_hit_distance,
  avg(adjusted_pctl_90_est_distance_30d) as proj_team_high_hit_distance
from lineup_detailed_stats
group by 1, 2, 3
order by 1, 2, 3), 

pitcher_log_raw as (
select
  game_date,
  game_pk,
  case when inning_topbot = 'Top' then 'Home' else 'Away' end as team, --check on this logic. Is it assigning team to hitter or pitcher?
  inning,
  at_bat_number,
  pitcher,
from `mlb_model_updated.pitch_level_data_2023_to_present`
group by all 
),
sp_list as (
select 
  game_date,
  game_pk,
  team,
  pitcher
from pitcher_log_raw
qualify  row_number() over(
    partition by game_pk, game_date, team
    order by at_bat_number
  ) = 1
),
pitcher_log_final_stage as (
select 
  sp.game_date,
  sp.game_pk,
  sp.pitcher,
  sp.team,
  gl.era_30d,
  gl.whip_30d,
  gl.avg_innings_30d,
  gl.avg_last_30_days,
  gl.obp_30d,
  gl.slugging_pct_30d,
  gl.ops_30d,
  gl.k_rate_30d,
  gl.whiff_rate_30d,
  gl.avg_velo_30d,
  gl.release_speed_10th_percentile_30d,
  gl.release_speed_90th_percentile_30d,
  gl.velo_stdev_30d,
  gl.hor_movement_median_30d,
  gl.hor_movement_stdev_30d,
  gl.vert_movement_median_30d,
  gl.vert_movement_stdev_30d,
  gl.med_launch_angle_30d,
  gl.med_launch_speed_30d,
  gl.perctile_90_launch_speed_30d,
  gl.med_est_distance_30d,
  gl.perctile_90_est_distance_30d
from sp_list sp
join `mlb_model_updated.pitcher_game_log_final` gl
  on sp.game_date = gl.game_date
  and sp.pitcher = gl.pitcher
  --TO DO: Join these fields. The GL table doesn't have the final two fields, so I'll have to add them in before I can do the join below
  --and sp.game_pk = gl.game_pk
  --and sp.team = gl.team 
order by 1, 2
),
final_scores as (
select 
  game_date,
  game_pk,
  max(post_away_score) as away_runs,
  max(post_home_score) as home_runs
from `mlb_model_updated.pitch_level_data_2023_to_present`
group by 1, 2
),
winner_check as (
select 
  game_date,
  game_pk,
  case when home_runs > away_runs then 1 else 0 end as home_winner_check
from final_scores)
select
  case 
    when l.team = 'Home' then w.home_winner_check
    when l.team = 'Away' then (case when w.home_winner_check = 1 then 0 else 1 end) 
  end as win_check,
  l.*,
  sp.* except(game_date, game_pk, team)
from lineups_final_stag l
join pitcher_log_final_stage sp
  on l.game_date = sp.game_date
  and l.game_pk = sp.game_pk
  and l.team = sp.team
join winner_check w
  on l.game_date = w.game_date
  and l.game_pk = w.game_pk
order by 3, 4
;

create or replace table `mlb_model_updated.inputs_for_regression` as 
select 
  s1.win_check,
  s1.game_date,
  s1.game_pk,
  s1.team,
  s1.proj_team_avg,
  s2.proj_team_avg as opponent_proj_avg,
  s1.proj_team_avg - s2.proj_team_avg as proj_avg_diff,
  s1.proj_team_obp - s2.proj_team_obp as proj_obp_diff,  
  s1.proj_team_slug - s2.proj_team_slug as proj_slug_diff,  
  s1.proj_team_ops - s2.proj_team_ops as proj_ops_diff,  
  s1.proj_team_k_rate - s2.proj_team_k_rate as proj_hit_k_rate_diff,  
  s1.proj_team_whiff_rate - s2.proj_team_whiff_rate as proj_hit_whiff_rate_diff,  
  s1.proj_team_med_launch_speed - s2.proj_team_med_launch_speed as proj_hit_med_launch_speed_diff,  
  s1.proj_team_high_launch_speed - s2.proj_team_high_launch_speed as proj_hit_high_launch_speed_diff,  
  s1.proj_team_med_launch_angle - s2.proj_team_med_launch_angle as proj_hit_med_launch_angle_diff,  
  s1.proj_team_med_hit_distance - s2.proj_team_med_hit_distance as proj_hit_med_hit_distance_diff,  
  s1.proj_team_high_hit_distance - s2.proj_team_high_hit_distance as proj_hit_high_hit_distance_diff,  
  s1.era_30d - s2.era_30d as proj_sp_era_diff,  
  s1.whip_30d - s2.whip_30d as proj_sp_whip_diff,  
  s1.obp_30d - s2.obp_30d as proj_sp_opp_obp_diff,  
  s1.slugging_pct_30d - s2.slugging_pct_30d as proj_sp_slug_diff,  
  s1.ops_30d - s2.ops_30d as proj_sp_ops_diff,  
  s1.k_rate_30d - s2.k_rate_30d as proj_sp_k_rate_diff,  
  s1.whiff_rate_30d - s2.whiff_rate_30d as proj_sp_whiff_rate_diff,  
  s1.avg_velo_30d - s2.avg_velo_30d as proj_sp_avg_velo_diff,  
  s1.release_speed_10th_percentile_30d - s2.release_speed_10th_percentile_30d as proj_release_speed_10th_pctl_diff,  
  s1.release_speed_90th_percentile_30d - s2.release_speed_90th_percentile_30d as proj_release_speed_90th_pctl_diff,  
  s1.velo_stdev_30d - s2.velo_stdev_30d as proj_sp_velo_stdev_diff,  
  s1.hor_movement_median_30d - s2.hor_movement_median_30d as proj_sp_hor_move_diff,  
  s1.hor_movement_stdev_30d - s2.hor_movement_stdev_30d as proj_sp_hor_move_stdev_diff,  
  s1.vert_movement_median_30d - s2.vert_movement_median_30d as proj_sp_vert_move_diff,  
  s1.vert_movement_stdev_30d - s2.vert_movement_stdev_30d as proj_sp_vert_move_stdev_diff,  
  s1.med_launch_angle_30d - s2.med_launch_angle_30d as proj_sp_med_launch_ang_diff,  
  s1.med_launch_speed_30d - s2.med_launch_speed_30d as proj_sp_med_launch_speed_diff,  
  s1.perctile_90_launch_speed_30d - s2.perctile_90_launch_speed_30d as proj_sp_high_launch_speed_diff,  
  s1.med_est_distance_30d - s2.med_est_distance_30d as proj_sp_med_launch_dist_diff,  
  s1.perctile_90_est_distance_30d - s2.perctile_90_est_distance_30d as proj_sp_high_launch_dist_diff  
from `mlb_model_updated.inputs_for_regression_stage` s1
join `mlb_model_updated.inputs_for_regression_stage` s2
  on s1.game_date = s2.game_date
  and s1.game_pk = s2.game_pk
  and s1.team != s2.team
where 
  s1.proj_team_avg is not null 
  and s2.proj_team_avg is not null
  and s1.era_30d is not null
  and s2.era_30d is not null
  and s1.med_launch_angle_30d is not null
  and s2.med_launch_angle_30d is not null
  and s1.vert_movement_median_30d is not null
  and s2.vert_movement_median_30d is not null
;

create or replace table `mlb_model_updated.inputs_for_regression2` as 
select 
  s1.win_check,
  s1.game_date,
  s1.game_pk,
  --s1.team,
  s1.proj_team_avg,
  s2.proj_team_avg as opponent_proj_avg,
  s1.proj_team_avg - s2.proj_team_avg as proj_avg_diff,
  s1.proj_team_obp - s2.proj_team_obp as proj_obp_diff,  
  s1.proj_team_slug - s2.proj_team_slug as proj_slug_diff,  
  s1.proj_team_ops - s2.proj_team_ops as proj_ops_diff,  
  s1.proj_team_k_rate - s2.proj_team_k_rate as proj_hit_k_rate_diff,  
  s1.proj_team_whiff_rate - s2.proj_team_whiff_rate as proj_hit_whiff_rate_diff,  
  s1.proj_team_med_launch_speed - s2.proj_team_med_launch_speed as proj_hit_med_launch_speed_diff,  
  s1.proj_team_high_launch_speed - s2.proj_team_high_launch_speed as proj_hit_high_launch_speed_diff,  
  s1.proj_team_med_launch_angle - s2.proj_team_med_launch_angle as proj_hit_med_launch_angle_diff,  
  s1.proj_team_med_hit_distance - s2.proj_team_med_hit_distance as proj_hit_med_hit_distance_diff,  
  s1.proj_team_high_hit_distance - s2.proj_team_high_hit_distance as proj_hit_high_hit_distance_diff,  
  s1.era_30d - s2.era_30d as proj_sp_era_diff,  
  s1.whip_30d - s2.whip_30d as proj_sp_whip_diff,  
  s1.obp_30d - s2.obp_30d as proj_sp_opp_obp_diff,  
  s1.slugging_pct_30d - s2.slugging_pct_30d as proj_sp_slug_diff,  
  s1.ops_30d - s2.ops_30d as proj_sp_ops_diff,  
  s1.k_rate_30d - s2.k_rate_30d as proj_sp_k_rate_diff,  
  s1.whiff_rate_30d - s2.whiff_rate_30d as proj_sp_whiff_rate_diff,  
  s1.avg_velo_30d - s2.avg_velo_30d as proj_sp_avg_velo_diff,  
  s1.release_speed_10th_percentile_30d - s2.release_speed_10th_percentile_30d as proj_release_speed_10th_pctl_diff,  
  s1.release_speed_90th_percentile_30d - s2.release_speed_90th_percentile_30d as proj_release_speed_90th_pctl_diff,  
  s1.velo_stdev_30d - s2.velo_stdev_30d as proj_sp_velo_stdev_diff,  
  s1.hor_movement_median_30d - s2.hor_movement_median_30d as proj_sp_hor_move_diff,  
  s1.hor_movement_stdev_30d - s2.hor_movement_stdev_30d as proj_sp_hor_move_stdev_diff,  
  s1.vert_movement_median_30d - s2.vert_movement_median_30d as proj_sp_vert_move_diff,  
  s1.vert_movement_stdev_30d - s2.vert_movement_stdev_30d as proj_sp_vert_move_stdev_diff,  
  s1.med_launch_angle_30d - s2.med_launch_angle_30d as proj_sp_med_launch_ang_diff,  
  s1.med_launch_speed_30d - s2.med_launch_speed_30d as proj_sp_med_launch_speed_diff,  
  s1.perctile_90_launch_speed_30d - s2.perctile_90_launch_speed_30d as proj_sp_high_launch_speed_diff,  
  s1.med_est_distance_30d - s2.med_est_distance_30d as proj_sp_med_launch_dist_diff,  
  s1.perctile_90_est_distance_30d - s2.perctile_90_est_distance_30d as proj_sp_high_launch_dist_diff  
from `mlb_model_updated.inputs_for_regression_stage` s1
join `mlb_model_updated.inputs_for_regression_stage` s2
  on s1.game_date = s2.game_date
  and s1.game_pk = s2.game_pk
  and s1.team != s2.team
where 
  s1.team = 'Home'
  and s1.proj_team_avg is not null 
  and s2.proj_team_avg is not null
  and s1.era_30d is not null
  and s2.era_30d is not null
  and s1.med_launch_angle_30d is not null
  and s2.med_launch_angle_30d is not null
  and s1.vert_movement_median_30d is not null
  and s2.vert_movement_median_30d is not null
;
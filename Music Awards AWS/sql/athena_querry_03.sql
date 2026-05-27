SELECT 
  has_any_major_award, 
  COUNT(*) AS total_songs, 
  AVG(duration_ms) AS avg_duration_ms, 
  ROUND(AVG(duration_ms) / 1000, 2) AS avg_duration_seconds, 
  ROUND(AVG(duration_ms) / 60000, 2) AS avg_duration_minutes 
FROM processed 
GROUP BY has_any_major_award;

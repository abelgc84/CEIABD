SELECT 
  has_any_major_award, 
  COUNT(*) AS total_songs, 
  AVG(danceability) AS avg_danceability, 
  AVG(energy) AS avg_energy, 
  AVG(valence) AS avg_valence, 
  AVG(tempo) AS avg_tempo 
FROM processed
GROUP BY has_any_major_award;

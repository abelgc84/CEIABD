WITH data AS ( 
  SELECT 
    CAST(year AS INTEGER) AS year, 
    danceability, 
    energy, 
    acousticness, 
    valence 
  FROM processed 
) 
SELECT 
  year, 
  AVG(danceability) AS avg_danceability, 
  AVG(energy) AS avg_energy, 
  AVG(acousticness) AS avg_acousticness, 
  AVG(valence) AS avg_valence, 
  COUNT(*) AS total_songs 
FROM data 
WHERE year >= 1950 
GROUP BY year ORDER BY year;

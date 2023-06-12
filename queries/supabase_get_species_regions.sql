SELECT
    species.species_id,
    ARRAY_AGG(ecoregion_species.eco_code) as ecoregions
FROM
    species
JOIN
    ecoregion_species ON species.species_id = ecoregion_species.species_id
GROUP BY
    species.species_id
LIMIT 100 - 0 OFFSET 0;

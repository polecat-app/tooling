SELECT
    species.species_id,
    ST_AsGeoJSON(ST_Union(ST_SimplifyPreserveTopology(ecoregion_shapes.geometry, 0.5)))
    AS geometry
FROM
    species
JOIN
    ecoregion_species ON species.species_id = ecoregion_species.species_id
JOIN
    ecoregion_shapes ON ecoregion_species.eco_code = ecoregion_shapes.eco_code
JOIN
    ecoregions ON ecoregion_shapes.eco_code = ecoregions.eco_code
WHERE
    species.species_id > 18020 AND species.species_id < 18022 AND ecoregions.area >
    6000
GROUP BY
    species.species_id
LIMIT 10;
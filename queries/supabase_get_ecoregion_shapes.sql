SELECT
    ecoregions.eco_code,
    ST_AsGeoJSON(ST_Union(ST_SimplifyPreserveTopology(ecoregion_shapes.geometry, 0.5)))
    AS geometry
FROM
    ecoregions
JOIN
    ecoregion_shapes ON ecoregions.eco_code = ecoregion_shapes.eco_code
GROUP BY
    ecoregions.eco_code;
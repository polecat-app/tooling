SELECT
    species.species_id,
    species.species,
    genus.genus_id,
    CASE WHEN species_ranking.score_binomial < species_ranking.score_common_name
         THEN species_ranking.score_binomial
         ELSE species_ranking.score_common_name
    END AS ranking,
    species_images.cover_url,
    species_images.thumbnail_name
FROM
    species
    LEFT JOIN species_ranking USING (species_id)
    LEFT JOIN genus USING (genus_id)
    LEFT JOIN "family" USING (family_id)
    LEFT JOIN "order" USING (order_id)
    LEFT JOIN class USING (class_id)
    LEFT JOIN species_images USING (species_id)
LIMIT 10;
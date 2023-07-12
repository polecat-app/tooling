with nocturnal_ids as(with
  nocturnal_species_table as (
    SELECT
      (
        SPLIT_PART(latin_name, ' ', 1) || ' ' || SPLIT_PART(latin_name, ' ', 2)
      ) AS latin_name, genus, species
    FROM
      nocturnal
  ),
  latin_name_table as (
    SELECT
      species_id,
      concat(genus, ' ', species) as latin_name
    from
      species
      left join genus using (genus_id)
  )
select
    species_id as species_id_nocturnal
from
  nocturnal_species_table
  left join latin_name_table using (latin_name)
where species_id is not null
order by genus)
update species_tags
set nocturnal = true
where species_id in (select species_id_nocturnal from nocturnal_ids)



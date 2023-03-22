# occupancy & unrentables, moves, online move ins, street / in place rate ratio

occupancy_sql = """
with dates as (
  select d::date as date  
	  from generate_series(
	    (now() - interval '7 days')::DATE
		,now()::DATE
	    ,'1 days') as d
)
, inactives as (
	select distinct on (f.site_code, u.id, d.date)
		f.site_code, d.date, u.id, u.width , u.length , uov.created_at, uov.value_before, uov.value_after, u.inactive
		, case when (uov.created_at < d.date or uov.created_at is null)
				then coalesce(uov.value_after::boolean, u.inactive, false) 
			when uov.created_at > d.date then uov.value_before::boolean end 
			"inactive_final" 
	from units u 
		inner join dates d on d.date >= u.created_at
		left join unit_occupancy_versions uov on uov.unit_id = u.id and uov.updated_column = 'inactive'
		inner join facilities f on f.id = u.facility_id 
	where (uov.created_at < d.date or uov.created_at is null) 
	order by f.site_code , u.id, d.date, uov.created_at desc 
)
, active_unit as (
	select d.date, ut.key, ut.unit_type_category_id as type_id, u.*, u.width * u.length as unit_area 
		, o.id as occ_id, o.move_in_date, o.move_out_date, o.moved_out
	from dates d 
	inner join units u on u.created_at <= d.date
            or (u.facility_id =333 and '2021-12-30' <= d.date)
    inner join unit_types ut on ut.id = u.unit_type_id 
	left join inactives i on i.id = u.id and i.date = d.date
	left join occupancies o on o.unit_id = u.id and o.move_in_date <= d.date 
		and (o.moved_out = false or (o.move_out_date::date > d.date and o.moved_out = true))
	where (i.id is null or i.inactive_final = false ) 
)
, all_tasks as (
    select f.id, u.id as unit_id, t.created_at::date, t.updated_at::date, t.completed_at::date, t.description , t.status, t.title as task_title
         , tt.title, ts.rentable 
    from tasks t
             left join units u on u.id = t.taskable_id
             left join task_templates tt on tt.id = t.task_template_id
             left join taskable_statuses ts on ts.id = t.taskable_status_id
             left join facilities f on f.id = u.facility_id
             left join unit_types ut on u.unit_type_id =ut.id 
    where lower(t.taskable_type) = 'unit'
      and ts.deleted_at is null
      and t.status != 2
      and ts.rentable = false 
)
, unrentable as (
	select uov.unit_id, uov.created_at as start_date,
		coalesce (lead(uov.created_at, 1)
		over (partition by uov.unit_id order by uov.created_at asc), now()+ interval '1 month') as end_date ,
		uov.value_after::boolean, uov.value_before::boolean 
	from unit_occupancy_versions uov 
	where uov.updated_column = 'unrentable'
)
, first_status as (
	select distinct on (u.id) u.id, u.facility_id, coalesce(ur.value_before, u.unrentable) as first_status,
		ur.start_date, ur.end_date
	from units u 
	left join unrentable ur on ur.unit_id = u.id 
	order by u.id, ur.start_date asc 
)
, unrentable_occupied_units as (
	select distinct on (u.id, d.date)
		f.id as facility_id, d.date,u.unit_number,u.id,u.width ,u.length ,ut.key,
		case when d.date >= o.move_in_date and (o.moved_out = false or (o.move_out_date::date > d.date and o.moved_out = true))
			then true
			else false end as occupied,
		case when ur.start_date::date > d.date then ur.value_before
			when ur.start_date::date <= d.date and ur.end_date::date > d.date then ur.value_after 
			else fs.first_status end as unrentable,
		at.title, at.task_title, at.description, at.created_at, at.rentable as task_rentable
	from dates d  
		inner join facilities f on 1=1
		inner join units u on u.facility_id = f.id 
		inner join unit_types ut on ut.id = u.unit_type_id 
		left join occupancies o on o.unit_id = u.id and d.date >= o.move_in_date and (o.moved_out = false or (o.moved_out = true and o.move_out_date > d.date))	
		left join all_tasks at on at.unit_id = u.id and at.created_at <=d.date
			and (at.status = 0 or at.completed_at > d.date or (at.status=1 and at.updated_at > d.date and at.completed_at is null))
		left join unrentable ur on ur.unit_id = u.id and d.date >= ur.start_date::date and d.date < ur.end_date::date
		left join first_status fs on fs.id = u.id 
)
, unrentable_units as (
	select 
		f.site_code ,ou.id,ou.width,ou.length,ou.width * ou.length as unit_area,ou.key,d.date,ou.unit_number,ou.occupied,ou.task_title
		,ou.title as task,ou.description,ou.created_at, (d.date - ou.created_at) as days_open
		, case when (lower(ou.title) like '%company unit%' or lower(ou.title) like '%trash%' or ou.task_title like '%Transfer%')
				or (ou.occupied = false and ou.task_rentable = false and (lower(ou.title) like '%clnrr%' or lower(ou.title) like '%ifnl%' or lower(ou.title) like '%wrong space%' 
				or lower(ou.title) like '%3rd party%' or lower(ou.title) like '%in house maintenance%')) 
				or (ou.occupied = false and lower(ou.title) like '%unit other%' and ou.task_rentable = false)
				or (ou.unrentable = true and ou.occupied = false and lower(ou.title) not like '%unit check%') then true 
		else false end as unrentable
	from dates d
		inner join unrentable_occupied_units ou on ou.date = d.date 
		left join facilities f on f.id = ou.facility_id 
	order by f.site_code , d.date 
)
	select 
		f.site_code,
		d.date,
		au.width,
		au.length,
		au.key as unit_type,
		au.type_id,
		count(distinct au.id) as units,
		au.unit_area,
		count(distinct au.id) * (au.unit_area) as nrsf,
		count(distinct au.occ_id) as occupied_units,
		count(distinct au.occ_id) filter(where au.move_out_date is null or au.move_out_date::date > d.date) as expected_occupied_units,
		count(distinct au.occ_id) * (au.width *au.length) as occupied_area ,
		count(distinct au.occ_id) filter(where uu.unrentable = true) as unrentable_occupied_units,
		count(uu.id) filter(where uu.unrentable = true) as unrentable_units ,
		count(uu2.id) * au.unit_area as unrentable_area
	from active_unit au
		inner join facilities f on f.id = au.facility_id 
		inner join dates d on d.date = au.date 
		left join unrentable_units uu on uu.id = au.id and d.date = uu.date 
		left join unrentable_units uu2 on uu2.id = au.id and d.date = uu2.date and uu2.unrentable = true 
	group by f.site_code, d.date, au.width , au.length, au.unit_area, au.key, au.type_id;
""" 

moves_sql = """
with dates as (
  select d::date as date  
	  from generate_series(
	    (now() - interval '14 days')::DATE
		,now()::DATE
	    ,'1 days') as d
)
, moves as (
	select distinct on (o.id)
		o.id
		, f.site_code
		, case when f.site_code = 'RD198' then '2021-12-30' 
			else f.created_at::date end as facility_created_date
		, u.width
		, u.length
		, u.width * u.length as unit_area
		, ut.key
		, o.move_in_date 
		, case when o.moved_out = true then o.move_out_date::date else null end as move_out_date 
		, o.move_out_date::date as scheduled_move_out
		, case when o.auctioned = true then 'auction'
			when lower(o.move_out_reason) like '%transfer%' then 'transfer' 
			else null end as status 
		, case when sum(l3.chg) < 0 then true else false end as promo 
		, coalesce(l.chg, o.monthly_rate) as move_in_rate
		, coalesce(sum(l2.chg), o.monthly_rate) as discount_move_in_rate
		, o.monthly_rate as move_out_rate 
	from occupancies o 
		inner join units u on u.id = o.unit_id 
		inner join facilities f on f.id = u.facility_id 
		inner join unit_types ut on ut.id = u.unit_type_id
		left join ledgers l on l.occupancy_id = o.id and l.charge_type =0 and l.chg > 0 and lower(l.description) not like '%description%'
		left join ledgers l2 on l2.occupancy_id = o.id and (l2.charge_type = 0 or l2.charge_type = 14 or l2.charge_type = 3
			or l2.charge_type =5 or l2.charge_type = 15) and lower(l2.description) not like '%description%'
			and date_trunc('month', l2.created_at) = date_trunc('month', o.move_in_date)
		left join ledgers l3 on l3.occupancy_id = o.id and (l3.charge_type = 14 or l3.charge_type = 15) 
			and l3.description not like '%Military%'
			and date_trunc('month', l3.created_at) = date_trunc('month', o.move_in_date)
		group by o.id, f.site_code , u.width , u.length ,ut.key,o.move_in_date , o.moved_out, o.auctioned,
			o.move_out_date , o.move_out_reason , l.chg,o.monthly_rate ,l.created_at , f.created_at 
		order by o.id, l.created_at asc
)
select 	
	d.date 
	, m.site_code
	, m.width
	, m.length
	, m.unit_area
	, m.key 
	, count(m.id) filter(where m.move_in_date = d.date) as move_ins 
	, count(m.id) filter(where m.move_out_date = d.date) as move_outs 
	, count(m.id) filter(where m.scheduled_move_out = d.date) as scheduled_move_outs
	, count(m.id) filter(where m.scheduled_move_out = d.date and m.status is null) as scheduled_move_outs_less_AT
	, count(m.id) filter(where m.move_in_date = d.date and m.status is null) as move_ins_less_AT
	, count(m.id) filter(where m.move_out_date = d.date and m.status is null) as move_outs_less_AT
	, sum(m.move_in_rate) filter(where m.move_in_date = d.date and m.status is null) as sum_mi_rates
	, sum(m.discount_move_in_rate) filter(where m.move_in_date = d.date and m.status is null) as sum_discount_mi_rates
	, sum(m.move_out_rate) filter(where m.move_out_date = d.date and m.status is null) as sum_mo_rates
from moves m
	inner join dates d on (d.date = m.move_in_date or d.date = m.move_out_date or d.date = m.scheduled_move_out)
		and d.date >= m.facility_created_date
group by d.date, m.site_code , m.width, m.length, m.unit_area , m.key ;
"""

online_moves_sql = """
select distinct on (o.id)
       f.site_code ,
       o.id, o.move_in_date, u.unit_number, u.width , u.length , u.climate_control 
		, case when o.sourceable_type = 'User' then 'Agent'
               when o.sourceable_type = 'ApplicationEntity' and o.sourceable_id = 2 then 'Customer Portal'
               when o.sourceable_type = 'ApplicationEntity' and o.sourceable_id = 4 then 'Kiosk'
               else null 
           end "Moved In By"
from occupancies o
inner join units u on o.unit_id = u.id
inner join facilities f on f.id = u.facility_id
where o.auctioned = false and o.move_in_date >= (now() - interval '1 month')::date
order by o.id ;
"""

street_ratio_sql = """
with dates as (
  select d::date as date  
	  from generate_series(
	    (now() - interval '1 year')::DATE
		,now()::DATE
	    ,'1 month') as d
)
, inactives as (
	select distinct on (f.site_code, u.id, d.date)
		f.site_code, d.date, u.id, u.width , u.length , uov.created_at, uov.value_before, uov.value_after, u.inactive
		, case when (uov.created_at < d.date or uov.created_at is null)
				then coalesce(uov.value_after::boolean, u.inactive, false) 
			when uov.created_at > d.date then uov.value_before::boolean end 
			"inactive_final" 
	from units u 
		inner join dates d on d.date >= u.created_at
		left join unit_occupancy_versions uov on uov.unit_id = u.id and uov.updated_column = 'inactive'
		inner join facilities f on f.id = u.facility_id 
	order by f.site_code , u.id, d.date, uov.created_at desc 
)
, active_unit_occs as (
	select d.date, ut.key, u.created_at unit_created_at, u.id u_unit_id, u.*, o.created_at occ_created_at, o.id occ_id, o.*
	from units u 
	inner join dates d on u.created_at <= d.date
            or (u.facility_id =333 and '2021-12-30' <= d.date)
    inner join unit_types ut on ut.id = u.unit_type_id and ut.unit_type_category_id =1 --only storage units 
	left join inactives i on i.id = u.id and i.date = d.date
	left join occupancies o on o.unit_id = u.id and o.move_in_date <= d.date 
		and (o.moved_out=false or (o.moved_out=true and o.move_out_date > d.date))
	where (i.id is null or i.inactive_final = false) 
)
, rate_changes as (
	SELECT
	    F.site_code
	  , F.id
	  , V.created_at at time zone 'UTC' at time zone f.time_zone                                        AS start_date
	  , coalesce (LEAD(V.created_at at time zone 'UTC' at time zone f.time_zone, 1)
	    OVER (PARTITION BY F.site_code, UC.width, UC.length, ut.key ORDER BY V.created_at at time zone 'UTC' at time zone f.time_zone ASC), now() + interval '1 month') AS end_date
	  , ((V.object_changes ->> 'street_price')::JSON ->> 0)::DOUBLE PRECISION                              AS initial_price
	  , ((V.object_changes ->> 'street_price')::JSON ->> 1)::DOUBLE PRECISION                              AS final_price
	  , UC.width
	  , UC.length
	  , ut.key
	  FROM
	    Versions                    V
	      LEFT JOIN Unit_Categories UC
	      ON UC.id = V.item_id
	      LEFT JOIN Facilities      F
	      ON F.id = UC.facility_id
	      left join unit_types ut on ut.id = UC.unit_type_id 
	  WHERE
	      V.item_type = 'UnitCategory'
	  AND V.object_changes::JSONB ? 'street_price'
)
, first_rate as (
	select distinct on (u.id) u.id, u.facility_id, u.width , u.length , ut.key , coalesce (rc.final_price, u.street_price) "first_street_rate", u.street_price, rc.start_date, rc.end_date
	from units u 
	left join unit_types ut on ut.id = u.unit_type_id 
	left join rate_changes rc on rc.id = u.facility_id and rc.width = u.width and rc.length = u.length and ut.key = rc.key
)
, street_rates as (
	select d.date, u.facility_id, sum(u.width * u.length) as nrsf,
		count(u.unit_id) as total_units
	, u.width , u.length , u.climate_control, u.key
		, round(sum( case when rc.final_price > 0 then rc.final_price
			   when rc.initial_price > 0 then rc.initial_price
			   else fr.first_street_rate
		 end )::numeric, 2) street_rate
	from active_unit_occs u 
	inner join facilities f on f.id = u.facility_id 
	inner join dates d on d.date = u.date -->= date(date_trunc('month', u.unit_created_at at time zone 'UTC' at time zone f.time_zone))
	left join first_rate fr on u.unit_id=fr.id
	left join rate_changes rc on rc.id = u.facility_id and rc.width = u.width and rc.length = u.length and rc.key = u.key
		and d.date >= rc.start_date::date and d.date < rc.end_date::date 
	group by d.date, u.facility_id , u.width , u.length , u.climate_control , u.key
)
, avg_tenant_rate_month as (
	select distinct on (d.date, o.id) d.date, u.facility_id ,u.length, u.width, ut.key, u.length * u.width as unit_area,
        o.id as occ_id,
		case when o.rate_last_changed_at is null or o.rate_last_changed_at::date <= d.date
            then o.monthly_rate
        when o.rate_last_changed_at::date > d.date 
            then o.monthly_rate - o.last_increase end as tenant_rate
	from dates d
	inner join units u on d.date >= u.created_at  
  	left join occupancies o on o.unit_id = u.id and o.move_in_date <= d.date and (o.moved_out=false or o.move_out_date > d.date)
  	inner join facilities f on u.facility_id = f.id 
  	inner join unit_types ut on u.unit_type_id = ut.id and ut.unit_type_category_id =1
)
select d.date
	, f.site_code
	, sr.width 
	, sr.length 
	, sr.key 
  	, sr.nrsf
  	, (t.unit_area * count(distinct t.occ_id)) as occupied_sf 
  	, sr.street_rate
  	, sum(t.tenant_rate) as "In Place Rate"
from dates d 
inner join facilities f on (f.id =333 and '2021-12-31' <= d.date) or f.created_at <= d.date  
left join street_rates sr on d.date=sr.date and f.id=sr.facility_id
left join avg_tenant_rate_month t on d.date=t.date and f.id=t.facility_id and t.width = sr.width and t.length = sr.length and sr.key = t.key
where f.site_code != 'RD042'
group by d.date, f.site_code, sr.width , sr.length , sr.key , sr.nrsf, t.unit_area, sr.street_rate
order by d.date, f.site_code;
"""

unrentables_sql = """
with dates as (
  select d::date as date  
	  from generate_series(
	    (now() - interval '7 days')::DATE
		,now()::DATE
	    ,'1 days') as d
)
, all_tasks as (
    select f.id
         , f.created_at       as facility_creation
         , u.unit_number
         , u.id as unit_id
         , u.width
         , u.length
         , u.width * u.length as area
         , ut.key
         , t.created_at::date
         , t.updated_at::date
         , t.completed_at::date
         , t.description
         , t.status
         , t.id as task_id
         , t.title as task_title
         , tt.title
         , tt.priority
         , tt.maintenance_task
         , tt.system_task
         , ts.type
         , ts.display_name
         , ts.rentable 
    from tasks t
             left join units u
                       on u.id = t.taskable_id
             left join task_templates tt
                       on tt.id = t.task_template_id
             left join taskable_statuses ts
                       on ts.id = t.taskable_status_id
             left join facilities f
                       on f.id = u.facility_id
             left join unit_types ut on u.unit_type_id =ut.id 
    where lower(t.taskable_type) = 'unit'
      and ts.deleted_at is null
      and u.inactive = false
      and t.status != 2
      and ts.rentable = false 
)
, unrentable as (
	select uov.unit_id,
		uov.created_at as start_date,
		coalesce (lead(uov.created_at, 1)
		over (partition by uov.unit_id order by uov.created_at asc), now()+ interval '1 month') as end_date ,
		uov.value_after::boolean,
		uov.value_before::boolean 
	from unit_occupancy_versions uov 
	where uov.updated_column = 'unrentable'
)
, first_status as (
	select distinct on (u.id) u.id, u.facility_id, coalesce(ur.value_before, u.unrentable) as first_status,
		ur.start_date, ur.end_date
	from units u 
	left join unrentable ur on ur.unit_id = u.id 
	order by u.id, ur.start_date
)
, unit_statuses as (
	select distinct on (u.id, d.date)
		f.id as facility_id,
		d.date,
		u.unit_number,
		u.id,
		u.width ,
		u.length ,
		ut.key,
		case when d.date >= o.move_in_date and (o.moved_out = false or (o.move_out_date::date >= d.date and o.moved_out = true))
			then true
			else false end as occupied,
		case when ur.start_date::date > d.date then ur.value_before
			when ur.start_date::date <= d.date and ur.end_date::date > d.date then ur.value_after 
			else fs.first_status end as unrentable,
		at.title,
		at.task_id,
		at.task_title,
		at.description,
		at.created_at,
		at.rentable as task_rentable
	from dates d 
		inner join facilities f on 1=1
		inner join units u on u.facility_id = f.id 
		inner join unit_types ut on ut.id = u.unit_type_id 
		left join occupancies o on o.unit_id = u.id and d.date >= o.move_in_date and (o.moved_out = false or (o.moved_out = true and o.move_out_date::date > d.date))	
		left join all_tasks at on at.unit_id = u.id and at.created_at <=d.date 
			and (at.status = 0 or at.completed_at::date > d.date or (at.status=1 and at.updated_at::date > d.date and at.completed_at is null))
		left join unrentable ur on ur.unit_id = u.id and d.date >= ur.start_date::date and d.date < ur.end_date::date
		left join first_status fs on fs.id = u.id 
		where u.inactive = false 
)
, rate_changes as (
	SELECT
	    F.site_code
	  , F.id
	  , V.created_at at time zone 'UTC' at time zone f.time_zone                                                                                      AS start_date
	  , coalesce (LEAD(V.created_at at time zone 'UTC' at time zone f.time_zone, 1)
	    OVER (PARTITION BY F.site_code, UC.width, UC.length, ut.key ORDER BY V.created_at at time zone 'UTC' at time zone f.time_zone ASC), now() + interval '1 month') AS end_date
	  , ((V.object_changes ->> 'street_price')::JSON ->> 0)::DOUBLE PRECISION                              AS initial_price
	  , ((V.object_changes ->> 'street_price')::JSON ->> 1)::DOUBLE PRECISION                              AS final_price
	  , UC.width
	  , UC.length
	  , ut.key
	  FROM
	    Versions                    V
	      LEFT JOIN Unit_Categories UC
	      ON UC.id = V.item_id
	      LEFT JOIN Facilities      F
	      ON F.id = UC.facility_id
	      left join unit_types ut on ut.id = UC.unit_type_id 
	  WHERE
	      V.item_type = 'UnitCategory'
	  AND V.object_changes::JSONB ? 'street_price'
)
, first_rate as (
	select distinct on (u.id) u.id, u.facility_id, u.width , u.length , ut.key , coalesce (rc.final_price, u.street_price) "first_street_rate", u.street_price, rc.start_date, rc.end_date
	from units u 
	left join unit_types ut on ut.id = u.unit_type_id 
	left join rate_changes rc on rc.id = u.facility_id and rc.width = u.width and rc.length = u.length and ut.key = rc.key
)
, street_rates as (
	select distinct on (u.id, d.date) d.date, u.facility_id, u.id
		, case when rc.final_price > 0 then rc.final_price
			   when rc.initial_price > 0 then rc.initial_price
			   else fr.first_street_rate
		 end street_rate
	from units u
	inner join unit_types ut on u.unit_type_id =ut.id 
	inner join facilities f on f.id = u.facility_id 
	inner join dates d on d.date >= (u.created_at at time zone 'UTC' at time zone f.time_zone)::date
	left join first_rate fr on u.id=fr.id
	left join rate_changes rc on rc.id = u.facility_id and rc.width = u.width and rc.length = u.length and rc.key = ut.key
		and d.date >= (rc.start_date)::date and d.date < (rc.end_date)::date 
	where u.inactive = false
)
, totals as (
	select 
		f.site_code 
		,us.id
		,us.width
		,us.length
		,us.width * us.length as unit_area
		,us.key
		,sr.street_rate
		,d.date 
		,us.unit_number
		,us.occupied
		,us.unrentable
		,us.task_title
		,us.task_id 
		,us.title as task
		,us.description
        ,us.created_at
		,(d.date - us.created_at) as days_open
		--I know this is crazy, but these were all the requirements the AMs gave me. the 'pending' status is used in the power bi report for individual units, not the roll ups.
		,case when (lower(us.title) like '%company unit%' or lower(us.title) like '%trash unit%' or us.task_title like '%Transfer%')
				or (us.occupied = false and us.task_rentable = false 
					and (lower(us.title) like '%clnrr%' or lower(us.title) like '%ifnl%' or lower(us.title) like '%wrong space%' or lower(us.title) like '%unit other%'
					or lower(us.title) like '%3rd party%' or lower(us.title) like '%in house maintenance%' or lower(us.title) like '%trash hauling%' or lower(us.title) like '%special auction%'
					or lower(us.title) like '%damaged unit%' or lower(us.title) like '%insurance claim inspection%' or lower(us.title) like '%no bid%'or lower(us.title) like '%towing%' 
					or lower(us.title) like '%parking unrentable%')) 
				or (us.unrentable = true and us.occupied = false and lower(us.title) not like '%unit check%') then 'unrentable'  
		when (us.occupied = true and (lower(us.title) like '%3rd party%' or lower(us.title) like '%in house maintenance%'))
			then 'pending' end as status
	from dates d
		inner join unit_statuses us on us.date = d.date 
		left join facilities f on f.id = us.facility_id 
		left join street_rates sr on d.date = sr.date and f.id = sr.facility_id and us.id = sr.id
	order by f.site_code , d.date 
)
	select distinct on (t.site_code, t.unit_number, t.date, t.task_id )
		t.*
	from totals t 
	where t.status = 'unrentable' and t.task != 'Company Unit' and t.task != 'Trash Unit'
	order by t.date desc;
"""
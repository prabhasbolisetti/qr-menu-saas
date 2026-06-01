-- Public menu production performance migration.
-- Run this in Supabase SQL editor. Indexes are CONCURRENTLY to avoid blocking writes.

alter table public.restaurants
add column if not exists is_open boolean not null default true;

alter table public.menu_items
add column if not exists is_bestseller boolean not null default false;

update public.menu_items
set is_bestseller = true
where is_special = true
  and is_bestseller = false;

create unique index concurrently if not exists restaurants_slug_unique
on public.restaurants (slug);

create index concurrently if not exists categories_restaurant_display_order_idx
on public.categories (restaurant_id, display_order, id);

create index concurrently if not exists menu_items_restaurant_available_display_order_idx
on public.menu_items (restaurant_id, is_available, display_order, id);

create index concurrently if not exists menu_items_restaurant_category_available_order_idx
on public.menu_items (restaurant_id, category_id, is_available, display_order, id);

create or replace function public.get_public_menu(menu_slug text)
returns jsonb
language sql
stable
security definer
set search_path = public
as $$
  with restaurant as (
    select
      id,
      name,
      logo_url,
      city,
      is_active,
      is_open
    from public.restaurants
    where slug = menu_slug
    limit 1
  )
  select
    case
      when r.id is null then null
      when r.is_active is false then jsonb_build_object(
        'inactive', true,
        'restaurant', jsonb_build_object(
          'id', r.id,
          'name', r.name,
          'logo_url', r.logo_url,
          'city', r.city,
          'is_open', coalesce(r.is_open, true)
        )
      )
      else jsonb_build_object(
        'restaurant', jsonb_build_object(
          'id', r.id,
          'name', r.name,
          'logo_url', r.logo_url,
          'city', r.city,
          'is_open', coalesce(r.is_open, true)
        ),
        'menu', coalesce(
          (
            select jsonb_agg(
              jsonb_build_object(
                'id', category_rows.id,
                'name', category_rows.name,
                'icon_emoji', category_rows.icon_emoji,
                'items', category_rows.items
              )
              order by category_rows.display_order, category_rows.name
            )
            from (
              select
                c.id,
                c.name,
                c.icon_emoji,
                c.display_order,
                items_by_category.items
              from public.categories c
              cross join lateral (
                select coalesce(
                  jsonb_agg(
                    jsonb_build_object(
                      'id', mi.id,
                      'name', mi.name,
                      'description', mi.description,
                      'price', mi.price,
                      'mrp_price', mi.mrp_price,
                      'image_url', mi.image_url,
                      'is_available', coalesce(mi.is_available, true),
                      'is_veg', coalesce(mi.is_veg, false),
                      'is_special', coalesce(mi.is_special, false),
                      'is_bestseller', coalesce(mi.is_bestseller, mi.is_special, false)
                    )
                    order by mi.display_order, mi.name
                  ),
                  '[]'::jsonb
                ) as items
                from public.menu_items mi
                where mi.restaurant_id = r.id
                  and mi.category_id = c.id
                  and mi.is_available = true
              ) items_by_category
              where c.restaurant_id = r.id
                and jsonb_array_length(items_by_category.items) > 0
            ) category_rows
          ),
          '[]'::jsonb
        )
      )
    end
  from restaurant r;
$$;

revoke all on function public.get_public_menu(text) from public;
grant execute on function public.get_public_menu(text) to service_role;

create or replace view public.qr_menu_required_column_audit as
with required_columns(table_name, column_name) as (
  values
    ('restaurants', 'id'),
    ('restaurants', 'slug'),
    ('restaurants', 'name'),
    ('restaurants', 'logo_url'),
    ('restaurants', 'city'),
    ('restaurants', 'is_active'),
    ('restaurants', 'is_open'),
    ('categories', 'id'),
    ('categories', 'restaurant_id'),
    ('categories', 'name'),
    ('categories', 'icon_emoji'),
    ('categories', 'display_order'),
    ('menu_items', 'id'),
    ('menu_items', 'restaurant_id'),
    ('menu_items', 'category_id'),
    ('menu_items', 'name'),
    ('menu_items', 'description'),
    ('menu_items', 'price'),
    ('menu_items', 'mrp_price'),
    ('menu_items', 'image_url'),
    ('menu_items', 'is_available'),
    ('menu_items', 'is_veg'),
    ('menu_items', 'is_special'),
    ('menu_items', 'is_bestseller'),
    ('menu_items', 'display_order')
)
select
  rc.table_name,
  rc.column_name,
  c.column_name is not null as exists_in_database
from required_columns rc
left join information_schema.columns c
  on c.table_schema = 'public'
 and c.table_name = rc.table_name
 and c.column_name = rc.column_name
order by rc.table_name, rc.column_name;

create or replace view public.qr_menu_required_index_audit as
with required_indexes(index_name) as (
  values
    ('restaurants_slug_unique'),
    ('categories_restaurant_display_order_idx'),
    ('menu_items_restaurant_available_display_order_idx'),
    ('menu_items_restaurant_category_available_order_idx')
)
select
  ri.index_name,
  i.indexname is not null as exists_in_database,
  i.indexdef
from required_indexes ri
left join pg_indexes i
  on i.schemaname = 'public'
 and i.indexname = ri.index_name
order by ri.index_name;

create or replace view public.qr_menu_unused_index_audit as
select
  schemaname,
  relname as table_name,
  indexrelname as index_name,
  idx_scan,
  idx_tup_read,
  idx_tup_fetch
from pg_stat_user_indexes
where schemaname = 'public'
  and relname in ('restaurants', 'categories', 'menu_items')
  and idx_scan = 0
order by relname, indexrelname;

create or replace function public.qr_menu_slow_query_audit()
returns table (
  query text,
  calls bigint,
  mean_exec_ms numeric,
  total_exec_ms numeric,
  rows_returned bigint
)
language plpgsql
security definer
set search_path = public
as $$
begin
  if to_regclass('pg_stat_statements') is null then
    return;
  end if;

  return query execute $audit$
    select
      query,
      calls,
      mean_exec_time::numeric as mean_exec_ms,
      total_exec_time::numeric as total_exec_ms,
      rows as rows_returned
    from pg_stat_statements
    where query ilike '%restaurants%'
       or query ilike '%categories%'
       or query ilike '%menu_items%'
       or query ilike '%get_public_menu%'
    order by mean_exec_time desc
    limit 20
  $audit$;
end;
$$;

revoke all on public.qr_menu_required_column_audit from public;
revoke all on public.qr_menu_required_index_audit from public;
revoke all on public.qr_menu_unused_index_audit from public;
revoke all on function public.qr_menu_slow_query_audit() from public;

grant select on public.qr_menu_required_column_audit to service_role;
grant select on public.qr_menu_required_index_audit to service_role;
grant select on public.qr_menu_unused_index_audit to service_role;
grant execute on function public.qr_menu_slow_query_audit() to service_role;

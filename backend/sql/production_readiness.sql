begin;

create extension if not exists pgcrypto;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  role text not null check (role in ('super', 'owner')),
  full_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.restaurants (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete restrict,
  name text not null check (length(trim(name)) between 2 and 120),
  slug text not null check (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
  city text not null check (length(trim(city)) between 2 and 80),
  logo_url text,
  is_active boolean not null default true,
  is_open boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  deleted_at timestamptz,
  deleted_by uuid references auth.users(id) on delete set null
);

create table if not exists public.categories (
  id uuid primary key default gen_random_uuid(),
  restaurant_id uuid not null references public.restaurants(id) on delete restrict,
  name text not null check (length(trim(name)) between 1 and 80),
  display_order integer not null default 0,
  icon_emoji text check (icon_emoji is null or length(icon_emoji) <= 16),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  deleted_at timestamptz,
  deleted_by uuid references auth.users(id) on delete set null
);

create table if not exists public.menu_items (
  id uuid primary key default gen_random_uuid(),
  restaurant_id uuid not null references public.restaurants(id) on delete restrict,
  category_id uuid not null references public.categories(id) on delete restrict,
  name text not null check (length(trim(name)) between 1 and 120),
  description text check (description is null or length(description) <= 500),
  price numeric(12, 2) not null check (price > 0),
  mrp_price numeric(12, 2) check (mrp_price is null or mrp_price >= 0),
  image_url text,
  is_available boolean not null default true,
  is_veg boolean not null default false,
  is_special boolean not null default false,
  is_bestseller boolean not null default false,
  display_order integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  deleted_at timestamptz,
  deleted_by uuid references auth.users(id) on delete set null,
  check (mrp_price is null or mrp_price >= price)
);

create table if not exists public.audit_logs (
  id uuid primary key default gen_random_uuid(),
  actor_id uuid references auth.users(id) on delete set null,
  actor_role text check (actor_role in ('super', 'owner')),
  action text not null,
  entity_type text not null,
  entity_id uuid,
  restaurant_id uuid references public.restaurants(id) on delete set null,
  entity jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

alter table public.profiles
  add column if not exists email text,
  add column if not exists role text,
  add column if not exists full_name text,
  add column if not exists created_at timestamptz not null default now(),
  add column if not exists updated_at timestamptz not null default now();

alter table public.restaurants
  add column if not exists owner_id uuid,
  add column if not exists name text,
  add column if not exists slug text,
  add column if not exists city text,
  add column if not exists logo_url text,
  add column if not exists is_active boolean not null default true,
  add column if not exists is_open boolean not null default true,
  add column if not exists created_at timestamptz not null default now(),
  add column if not exists updated_at timestamptz not null default now(),
  add column if not exists deleted_at timestamptz,
  add column if not exists deleted_by uuid references auth.users(id) on delete set null;

alter table public.categories
  add column if not exists restaurant_id uuid,
  add column if not exists name text,
  add column if not exists display_order integer not null default 0,
  add column if not exists icon_emoji text,
  add column if not exists created_at timestamptz not null default now(),
  add column if not exists updated_at timestamptz not null default now(),
  add column if not exists deleted_at timestamptz,
  add column if not exists deleted_by uuid references auth.users(id) on delete set null;

alter table public.menu_items
  add column if not exists restaurant_id uuid,
  add column if not exists category_id uuid,
  add column if not exists name text,
  add column if not exists description text,
  add column if not exists price numeric(12, 2),
  add column if not exists mrp_price numeric(12, 2),
  add column if not exists image_url text,
  add column if not exists is_available boolean not null default true,
  add column if not exists is_veg boolean not null default false,
  add column if not exists is_special boolean not null default false,
  add column if not exists is_bestseller boolean not null default false,
  add column if not exists display_order integer not null default 0,
  add column if not exists created_at timestamptz not null default now(),
  add column if not exists updated_at timestamptz not null default now(),
  add column if not exists deleted_at timestamptz,
  add column if not exists deleted_by uuid references auth.users(id) on delete set null;

update public.menu_items
set is_bestseller = true
where is_special = true
  and is_bestseller = false;

insert into public.profiles (id, email, role, full_name)
select
  id,
  email,
  raw_app_meta_data->>'role',
  raw_user_meta_data->>'full_name'
from auth.users
where raw_app_meta_data->>'role' in ('super', 'owner')
on conflict (id) do update set
  email = excluded.email,
  full_name = coalesce(public.profiles.full_name, excluded.full_name),
  updated_at = now();

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists profiles_set_updated_at on public.profiles;
create trigger profiles_set_updated_at
before update on public.profiles
for each row execute function public.set_updated_at();

drop trigger if exists restaurants_set_updated_at on public.restaurants;
create trigger restaurants_set_updated_at
before update on public.restaurants
for each row execute function public.set_updated_at();

drop trigger if exists categories_set_updated_at on public.categories;
create trigger categories_set_updated_at
before update on public.categories
for each row execute function public.set_updated_at();

drop trigger if exists menu_items_set_updated_at on public.menu_items;
create trigger menu_items_set_updated_at
before update on public.menu_items
for each row execute function public.set_updated_at();

create or replace function public.sync_profile_email_from_auth_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  update public.profiles
  set
    email = new.email,
    full_name = coalesce(public.profiles.full_name, new.raw_user_meta_data->>'full_name'),
    updated_at = now()
  where id = new.id;

  return new;
end;
$$;

drop trigger if exists sync_profile_from_auth_user on auth.users;
drop trigger if exists sync_profile_email_from_auth_user on auth.users;
create trigger sync_profile_email_from_auth_user
after update of email, raw_user_meta_data on auth.users
for each row execute function public.sync_profile_email_from_auth_user();

create or replace function public.current_profile_role()
returns text
language sql
stable
security definer
set search_path = public
as $$
  select p.role
  from public.profiles p
  where p.id = auth.uid()
  limit 1
$$;

create or replace function public.is_super_admin()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select coalesce(public.current_profile_role() = 'super', false)
$$;

create or replace function public.owns_restaurant(target_restaurant_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1
    from public.restaurants r
    where r.id = target_restaurant_id
      and r.owner_id = auth.uid()
      and r.deleted_at is null
  )
$$;

create or replace function public.guard_profile_role_changes()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if auth.role() = 'service_role' or auth.uid() is null then
    return new;
  end if;

  if tg_op = 'INSERT' and new.role = 'super' and not public.is_super_admin() then
    raise exception 'Only an existing super admin can create a super profile';
  end if;

  if tg_op = 'UPDATE' and new.role is distinct from old.role and not public.is_super_admin() then
    raise exception 'Only a super admin can change profile roles';
  end if;

  return new;
end;
$$;

drop trigger if exists profiles_guard_role_changes on public.profiles;
create trigger profiles_guard_role_changes
before insert or update on public.profiles
for each row execute function public.guard_profile_role_changes();

create or replace function public.guard_restaurant_owner_changes()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if auth.role() = 'service_role' or auth.uid() is null or public.is_super_admin() then
    return new;
  end if;

  if tg_op = 'UPDATE' and new.owner_id is distinct from old.owner_id then
    raise exception 'Restaurant ownership cannot be changed by owners';
  end if;

  return new;
end;
$$;

drop trigger if exists restaurants_guard_owner_changes on public.restaurants;
create trigger restaurants_guard_owner_changes
before update on public.restaurants
for each row execute function public.guard_restaurant_owner_changes();

create or replace function public.prevent_hard_delete()
returns trigger
language plpgsql
as $$
begin
  raise exception 'Hard deletes are disabled; update deleted_at instead';
end;
$$;

drop trigger if exists restaurants_prevent_hard_delete on public.restaurants;
create trigger restaurants_prevent_hard_delete
before delete on public.restaurants
for each row execute function public.prevent_hard_delete();

drop trigger if exists categories_prevent_hard_delete on public.categories;
create trigger categories_prevent_hard_delete
before delete on public.categories
for each row execute function public.prevent_hard_delete();

drop trigger if exists menu_items_prevent_hard_delete on public.menu_items;
create trigger menu_items_prevent_hard_delete
before delete on public.menu_items
for each row execute function public.prevent_hard_delete();

alter table public.restaurants
drop constraint if exists restaurants_owner_id_fkey;
alter table public.restaurants
add constraint restaurants_owner_id_fkey
foreign key (owner_id) references auth.users(id) on delete restrict not valid;

alter table public.categories
drop constraint if exists categories_restaurant_id_fkey;
alter table public.categories
add constraint categories_restaurant_id_fkey
foreign key (restaurant_id) references public.restaurants(id) on delete restrict not valid;

alter table public.menu_items
drop constraint if exists menu_items_restaurant_id_fkey;
alter table public.menu_items
add constraint menu_items_restaurant_id_fkey
foreign key (restaurant_id) references public.restaurants(id) on delete restrict not valid;

alter table public.menu_items
drop constraint if exists menu_items_category_id_fkey;
alter table public.menu_items
add constraint menu_items_category_id_fkey
foreign key (category_id) references public.categories(id) on delete restrict not valid;

drop index if exists restaurants_owner_id_unique;
drop index if exists restaurants_slug_unique;
drop index if exists restaurants_public_slug_cover_idx;
drop index if exists categories_restaurant_deleted_display_order_idx;
drop index if exists menu_items_restaurant_deleted_display_order_idx;
drop index if exists menu_items_restaurant_category_deleted_order_idx;
drop index if exists menu_items_public_available_category_order_idx;

create unique index restaurants_owner_id_unique
on public.restaurants (owner_id)
where deleted_at is null;

create unique index restaurants_slug_unique
on public.restaurants (slug)
where deleted_at is null;

create index if not exists profiles_role_idx
on public.profiles (role);

create index if not exists restaurants_owner_deleted_idx
on public.restaurants (owner_id, deleted_at);

create index restaurants_public_slug_cover_idx
on public.restaurants (slug, deleted_at)
include (id, name, logo_url, city, is_active, is_open);

create index categories_restaurant_deleted_display_order_idx
on public.categories (restaurant_id, deleted_at, display_order, id);

create unique index if not exists categories_id_restaurant_id_unique
on public.categories (id, restaurant_id);

create index menu_items_restaurant_deleted_display_order_idx
on public.menu_items (restaurant_id, deleted_at, display_order, id);

create index menu_items_restaurant_category_deleted_order_idx
on public.menu_items (restaurant_id, category_id, deleted_at, display_order, id);

create index menu_items_public_available_category_order_idx
on public.menu_items (restaurant_id, category_id, display_order, id)
where is_available = true and deleted_at is null;

create index if not exists audit_logs_restaurant_created_idx
on public.audit_logs (restaurant_id, created_at desc);

create index if not exists audit_logs_actor_created_idx
on public.audit_logs (actor_id, created_at desc);

alter table public.menu_items
drop constraint if exists menu_items_category_restaurant_match;
alter table public.menu_items
add constraint menu_items_category_restaurant_match
foreign key (category_id, restaurant_id)
references public.categories (id, restaurant_id)
on delete restrict not valid;

alter table public.profiles enable row level security;
alter table public.restaurants enable row level security;
alter table public.categories enable row level security;
alter table public.menu_items enable row level security;
alter table public.audit_logs enable row level security;

alter table public.profiles force row level security;
alter table public.restaurants force row level security;
alter table public.categories force row level security;
alter table public.menu_items force row level security;
alter table public.audit_logs force row level security;

drop policy if exists profiles_select_self_or_super on public.profiles;
create policy profiles_select_self_or_super
on public.profiles
for select
to authenticated
using (id = auth.uid() or public.is_super_admin());

drop policy if exists profiles_insert_super_only on public.profiles;
create policy profiles_insert_super_only
on public.profiles
for insert
to authenticated
with check (public.is_super_admin());

drop policy if exists profiles_update_super_only on public.profiles;
create policy profiles_update_super_only
on public.profiles
for update
to authenticated
using (public.is_super_admin())
with check (role in ('super', 'owner'));

drop policy if exists restaurants_select_owner_or_super on public.restaurants;
create policy restaurants_select_owner_or_super
on public.restaurants
for select
to authenticated
using (
  deleted_at is null
  and (public.is_super_admin() or owner_id = auth.uid())
);

drop policy if exists restaurants_insert_super_only on public.restaurants;
create policy restaurants_insert_super_only
on public.restaurants
for insert
to authenticated
with check (public.is_super_admin());

drop policy if exists restaurants_update_owner_or_super on public.restaurants;
create policy restaurants_update_owner_or_super
on public.restaurants
for update
to authenticated
using (
  deleted_at is null
  and (public.is_super_admin() or owner_id = auth.uid())
)
with check (
  public.is_super_admin() or owner_id = auth.uid()
);

drop policy if exists categories_select_owner_or_super on public.categories;
create policy categories_select_owner_or_super
on public.categories
for select
to authenticated
using (
  deleted_at is null
  and (public.is_super_admin() or public.owns_restaurant(restaurant_id))
);

drop policy if exists categories_insert_owner_or_super on public.categories;
create policy categories_insert_owner_or_super
on public.categories
for insert
to authenticated
with check (public.is_super_admin() or public.owns_restaurant(restaurant_id));

drop policy if exists categories_update_owner_or_super on public.categories;
create policy categories_update_owner_or_super
on public.categories
for update
to authenticated
using (public.is_super_admin() or public.owns_restaurant(restaurant_id))
with check (public.is_super_admin() or public.owns_restaurant(restaurant_id));

drop policy if exists menu_items_select_owner_or_super on public.menu_items;
create policy menu_items_select_owner_or_super
on public.menu_items
for select
to authenticated
using (
  deleted_at is null
  and (public.is_super_admin() or public.owns_restaurant(restaurant_id))
);

drop policy if exists menu_items_insert_owner_or_super on public.menu_items;
create policy menu_items_insert_owner_or_super
on public.menu_items
for insert
to authenticated
with check (public.is_super_admin() or public.owns_restaurant(restaurant_id));

drop policy if exists menu_items_update_owner_or_super on public.menu_items;
create policy menu_items_update_owner_or_super
on public.menu_items
for update
to authenticated
using (public.is_super_admin() or public.owns_restaurant(restaurant_id))
with check (public.is_super_admin() or public.owns_restaurant(restaurant_id));

drop policy if exists audit_logs_select_owner_or_super on public.audit_logs;
create policy audit_logs_select_owner_or_super
on public.audit_logs
for select
to authenticated
using (
  public.is_super_admin()
  or (
    restaurant_id is not null
    and public.owns_restaurant(restaurant_id)
  )
);

drop policy if exists audit_logs_insert_owner_or_super on public.audit_logs;

revoke all on table public.profiles from anon;
revoke all on table public.restaurants from anon;
revoke all on table public.categories from anon;
revoke all on table public.menu_items from anon;
revoke all on table public.audit_logs from anon;

grant usage on schema public to authenticated;
grant select, insert, update on table public.profiles to authenticated;
grant select, insert, update on table public.restaurants to authenticated;
grant select, insert, update on table public.categories to authenticated;
grant select, insert, update on table public.menu_items to authenticated;
grant select on table public.audit_logs to authenticated;

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
      and deleted_at is null
    limit 1
  ),
  items_by_category as (
    select
      mi.restaurant_id,
      mi.category_id,
      jsonb_agg(
        jsonb_build_object(
          'id', mi.id,
          'name', mi.name,
          'description', mi.description,
          'price', mi.price,
          'mrp_price', mi.mrp_price,
          'image_url', mi.image_url,
          'is_available', true,
          'is_veg', coalesce(mi.is_veg, false),
          'is_special', coalesce(mi.is_special, false),
          'is_bestseller', coalesce(mi.is_bestseller, mi.is_special, false)
        )
        order by mi.display_order, mi.name
      ) as items
    from public.menu_items mi
    join restaurant r
      on r.id = mi.restaurant_id
     and r.is_active is true
    join public.categories c
      on c.id = mi.category_id
     and c.restaurant_id = mi.restaurant_id
     and c.deleted_at is null
    where mi.is_available = true
      and mi.deleted_at is null
    group by mi.restaurant_id, mi.category_id
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
              category_rows.category_payload
              order by category_rows.display_order, category_rows.category_name
            )
            from (
              select
                c.display_order,
                c.name as category_name,
                jsonb_build_object(
                  'id', c.id,
                  'name', c.name,
                  'icon_emoji', c.icon_emoji,
                  'items', items_by_category.items
                ) as category_payload
              from public.categories c
              join items_by_category
                on items_by_category.category_id = c.id
               and items_by_category.restaurant_id = c.restaurant_id
              where c.restaurant_id = r.id
                and c.deleted_at is null
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

create or replace view public.qr_menu_rls_audit as
select
  n.nspname as schema_name,
  c.relname as table_name,
  c.relrowsecurity as rls_enabled,
  c.relforcerowsecurity as rls_forced
from pg_class c
join pg_namespace n
  on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relname in ('profiles', 'restaurants', 'categories', 'menu_items', 'audit_logs')
order by c.relname;

create or replace view public.qr_menu_policy_audit as
select
  schemaname,
  tablename,
  policyname,
  roles,
  cmd,
  qual,
  with_check
from pg_policies
where schemaname = 'public'
  and tablename in ('profiles', 'restaurants', 'categories', 'menu_items', 'audit_logs')
order by tablename, policyname;

create or replace view public.qr_menu_required_index_audit as
with required_indexes(index_name) as (
  values
    ('profiles_role_idx'),
    ('restaurants_owner_id_unique'),
    ('restaurants_slug_unique'),
    ('restaurants_owner_deleted_idx'),
    ('restaurants_public_slug_cover_idx'),
    ('categories_restaurant_deleted_display_order_idx'),
    ('categories_id_restaurant_id_unique'),
    ('menu_items_restaurant_deleted_display_order_idx'),
    ('menu_items_restaurant_category_deleted_order_idx'),
    ('menu_items_public_available_category_order_idx'),
    ('audit_logs_restaurant_created_idx'),
    ('audit_logs_actor_created_idx')
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

create or replace view public.qr_menu_tenant_isolation_audit as
select
  'restaurants' as table_name,
  count(*) filter (where owner_id is null) as unsafe_rows
from public.restaurants
where deleted_at is null
union all
select
  'categories',
  count(*) filter (where r.id is null) as unsafe_rows
from public.categories c
left join public.restaurants r
  on r.id = c.restaurant_id
where c.deleted_at is null
union all
select
  'menu_items',
  count(*) filter (where r.id is null or c.id is null or c.restaurant_id <> mi.restaurant_id) as unsafe_rows
from public.menu_items mi
left join public.restaurants r
  on r.id = mi.restaurant_id
left join public.categories c
  on c.id = mi.category_id
where mi.deleted_at is null;

revoke all on public.qr_menu_rls_audit from public;
revoke all on public.qr_menu_policy_audit from public;
revoke all on public.qr_menu_required_index_audit from public;
revoke all on public.qr_menu_tenant_isolation_audit from public;

grant select on public.qr_menu_rls_audit to service_role;
grant select on public.qr_menu_policy_audit to service_role;
grant select on public.qr_menu_required_index_audit to service_role;
grant select on public.qr_menu_tenant_isolation_audit to service_role;

commit;

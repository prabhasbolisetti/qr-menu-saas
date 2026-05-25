begin;

alter table public.restaurants
add column if not exists is_open boolean not null default true;

alter table public.menu_items
add column if not exists is_bestseller boolean not null default false;

update public.menu_items
set is_bestseller = true
where is_special = true
  and is_bestseller = false;

delete from public.menu_items mi
where not exists (
  select 1
  from public.restaurants r
  where r.id = mi.restaurant_id
);

delete from public.menu_items mi
where not exists (
  select 1
  from public.categories c
  where c.id = mi.category_id
    and c.restaurant_id = mi.restaurant_id
);

delete from public.categories c
where not exists (
  select 1
  from public.restaurants r
  where r.id = c.restaurant_id
);

create unique index if not exists restaurants_owner_id_unique
on public.restaurants (owner_id);

create unique index if not exists restaurants_slug_unique
on public.restaurants (slug);

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text,
  role text not null check (role in ('super', 'owner')),
  full_name text,
  created_at timestamptz not null default now()
);

insert into public.profiles (id, email, role, full_name)
select
  id,
  email,
  coalesce(raw_app_meta_data->>'role', raw_user_meta_data->>'role') as role,
  raw_user_meta_data->>'full_name' as full_name
from auth.users
where coalesce(raw_app_meta_data->>'role', raw_user_meta_data->>'role') in ('super', 'owner')
on conflict (id) do update set
  email = excluded.email,
  role = excluded.role,
  full_name = coalesce(public.profiles.full_name, excluded.full_name);

create or replace function public.sync_profile_from_auth_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  user_role text;
begin
  user_role := coalesce(new.raw_app_meta_data->>'role', new.raw_user_meta_data->>'role');

  if user_role in ('super', 'owner') then
    insert into public.profiles (id, email, role, full_name)
    values (
      new.id,
      new.email,
      user_role,
      new.raw_user_meta_data->>'full_name'
    )
    on conflict (id) do update set
      email = excluded.email,
      role = excluded.role,
      full_name = coalesce(public.profiles.full_name, excluded.full_name);
  end if;

  return new;
end;
$$;

drop trigger if exists sync_profile_from_auth_user on auth.users;

create trigger sync_profile_from_auth_user
after insert or update of email, raw_app_meta_data, raw_user_meta_data on auth.users
for each row execute function public.sync_profile_from_auth_user();

create index if not exists categories_restaurant_id_idx
on public.categories (restaurant_id);

create index if not exists menu_items_restaurant_id_idx
on public.menu_items (restaurant_id);

create index if not exists menu_items_category_id_idx
on public.menu_items (category_id);

create unique index if not exists categories_id_restaurant_id_unique
on public.categories (id, restaurant_id);

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'restaurants_owner_id_fkey'
  ) then
    alter table public.restaurants
    add constraint restaurants_owner_id_fkey
    foreign key (owner_id) references auth.users(id) on delete cascade;
  end if;

  if not exists (
    select 1 from pg_constraint where conname = 'categories_restaurant_id_fkey'
  ) then
    alter table public.categories
    add constraint categories_restaurant_id_fkey
    foreign key (restaurant_id) references public.restaurants(id) on delete cascade;
  end if;

  if not exists (
    select 1 from pg_constraint where conname = 'menu_items_restaurant_id_fkey'
  ) then
    alter table public.menu_items
    add constraint menu_items_restaurant_id_fkey
    foreign key (restaurant_id) references public.restaurants(id) on delete cascade;
  end if;

  if not exists (
    select 1 from pg_constraint where conname = 'menu_items_category_id_fkey'
  ) then
    alter table public.menu_items
    add constraint menu_items_category_id_fkey
    foreign key (category_id) references public.categories(id) on delete cascade;
  end if;
end $$;

alter table public.menu_items
drop constraint if exists menu_items_category_restaurant_match;

alter table public.menu_items
add constraint menu_items_category_restaurant_match
foreign key (category_id, restaurant_id)
references public.categories (id, restaurant_id)
on delete cascade;

commit;

-- Optional deterministic demo data after auth users exist.
-- Run backend/seed_demo.py to create the Supabase auth users and seed Burger Empire safely.

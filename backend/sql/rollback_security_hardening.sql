begin;

drop view if exists public.qr_menu_tenant_isolation_audit;
drop view if exists public.qr_menu_required_index_audit;
drop view if exists public.qr_menu_policy_audit;
drop view if exists public.qr_menu_rls_audit;

drop policy if exists audit_logs_insert_owner_or_super on public.audit_logs;
drop policy if exists audit_logs_select_owner_or_super on public.audit_logs;
drop policy if exists menu_items_update_owner_or_super on public.menu_items;
drop policy if exists menu_items_insert_owner_or_super on public.menu_items;
drop policy if exists menu_items_select_owner_or_super on public.menu_items;
drop policy if exists categories_update_owner_or_super on public.categories;
drop policy if exists categories_insert_owner_or_super on public.categories;
drop policy if exists categories_select_owner_or_super on public.categories;
drop policy if exists restaurants_update_owner_or_super on public.restaurants;
drop policy if exists restaurants_insert_super_only on public.restaurants;
drop policy if exists restaurants_select_owner_or_super on public.restaurants;
drop policy if exists profiles_update_super_only on public.profiles;
drop policy if exists profiles_insert_super_only on public.profiles;
drop policy if exists profiles_select_self_or_super on public.profiles;

alter table if exists public.audit_logs no force row level security;
alter table if exists public.menu_items no force row level security;
alter table if exists public.categories no force row level security;
alter table if exists public.restaurants no force row level security;
alter table if exists public.profiles no force row level security;

alter table if exists public.audit_logs disable row level security;
alter table if exists public.menu_items disable row level security;
alter table if exists public.categories disable row level security;
alter table if exists public.restaurants disable row level security;
alter table if exists public.profiles disable row level security;

drop trigger if exists menu_items_prevent_hard_delete on public.menu_items;
drop trigger if exists categories_prevent_hard_delete on public.categories;
drop trigger if exists restaurants_prevent_hard_delete on public.restaurants;
drop trigger if exists restaurants_guard_owner_changes on public.restaurants;
drop trigger if exists profiles_guard_role_changes on public.profiles;
drop trigger if exists sync_profile_email_from_auth_user on auth.users;

drop function if exists public.prevent_hard_delete();
drop function if exists public.guard_restaurant_owner_changes();
drop function if exists public.guard_profile_role_changes();
drop function if exists public.owns_restaurant(uuid);
drop function if exists public.is_super_admin();
drop function if exists public.current_profile_role();
drop function if exists public.sync_profile_email_from_auth_user();

commit;

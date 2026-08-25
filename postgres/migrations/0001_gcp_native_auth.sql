begin;

create extension if not exists pgcrypto;
create type public.app_role as enum ('DESIGNER', 'MONITOR');

create table public.app_users (
    id uuid primary key default gen_random_uuid(),
    email text not null,
    password_hash text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint app_users_email_normalized check (email = lower(btrim(email))),
    constraint app_users_email_format check (
        char_length(email) between 3 and 320 and email ~ '^[^@[:space:]]+@[^@[:space:]]+$'
    ),
    constraint app_users_password_hash_format check (password_hash like 'scrypt$%')
);
create unique index app_users_email_unique_idx on public.app_users (email);

create table public.profiles (
    id uuid primary key references public.app_users (id) on delete cascade,
    display_name text not null,
    role public.app_role not null,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint profiles_display_name_not_blank
        check (char_length(btrim(display_name)) between 1 and 120)
);
create index profiles_role_active_idx on public.profiles (role, is_active);

create schema private;
create function private.set_updated_at()
returns trigger language plpgsql set search_path = '' as $$
begin
    new.updated_at := now();
    return new;
end;
$$;
create trigger app_users_set_updated_at before update on public.app_users
for each row execute function private.set_updated_at();
create trigger profiles_set_updated_at before update on public.profiles
for each row execute function private.set_updated_at();

commit;

create table if not exists licenses (
    id uuid primary key default gen_random_uuid(),
    license_key varchar(64) not null unique,
    user_email varchar(255) not null,
    hwid varchar(255),
    hostname varchar(255),
    status varchar(32) not null default 'TRIAL',
    plan_type varchar(32) not null default 'FREE_TRIAL_7D',
    max_devices integer not null default 1,
    hwid_resets_left integer not null default 3,
    starts_at timestamptz,
    expires_at timestamptz not null,
    is_revoked boolean not null default false,
    revoked_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_licenses_key on licenses (license_key);
create index if not exists idx_licenses_email on licenses (user_email);
create index if not exists idx_licenses_hwid on licenses (hwid);
create index if not exists idx_licenses_expires_at on licenses (expires_at);

alter table licenses enable row level security;

create policy "service_full_access" on licenses
    for all
    using (auth.role() = 'service_role')
    with check (auth.role() = 'service_role');
